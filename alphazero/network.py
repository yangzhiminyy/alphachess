from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class NetworkConfig:
	"""Generic policy-value network configuration."""
	input_channels: int
	board_height: int
	board_width: int
	action_size: int
	hidden_channels: int = 64
	num_res_blocks: int = 3


class ResidualBlock(nn.Module):
	def __init__(self, channels: int) -> None:
		super().__init__()
		self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
		self.bn1 = nn.BatchNorm2d(channels)
		self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
		self.bn2 = nn.BatchNorm2d(channels)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		res = x
		x = F.relu(self.bn1(self.conv1(x)))
		x = self.bn2(self.conv2(x))
		x = F.relu(x + res)
		return x


class PolicyValueNet(nn.Module):
	"""Generic CNN policy-value network for board games."""
	
	def __init__(self, config: NetworkConfig) -> None:
		super().__init__()
		self.config = config
		
		# Stem
		self.stem = nn.Conv2d(config.input_channels, config.hidden_channels, kernel_size=3, padding=1)
		self.stem_bn = nn.BatchNorm2d(config.hidden_channels)
		
		# Residual blocks
		self.blocks = nn.ModuleList([
			ResidualBlock(config.hidden_channels) for _ in range(config.num_res_blocks)
		])
		
		# Policy head
		self.p_conv = nn.Conv2d(config.hidden_channels, 32, kernel_size=1)
		self.p_bn = nn.BatchNorm2d(32)
		self.p_fc = nn.Linear(32 * config.board_height * config.board_width, config.action_size)
		
		# Value head
		self.v_conv = nn.Conv2d(config.hidden_channels, 32, kernel_size=1)
		self.v_bn = nn.BatchNorm2d(32)
		self.v_fc1 = nn.Linear(32 * config.board_height * config.board_width, 128)
		self.v_fc2 = nn.Linear(128, 1)
	
	def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
		# Shared trunk
		x = F.relu(self.stem_bn(self.stem(x)))
		for blk in self.blocks:
			x = blk(x)
		
		# Policy head
		p = F.relu(self.p_bn(self.p_conv(x)))
		p = p.reshape(p.size(0), -1)
		p = self.p_fc(p)
		
		# Value head
		v = F.relu(self.v_bn(self.v_conv(x)))
		v = v.reshape(v.size(0), -1)
		v = F.relu(self.v_fc1(v))
		v = torch.tanh(self.v_fc2(v))
		
		return p, v.squeeze(-1)


def create_xiangqi_net() -> PolicyValueNet:
	"""Factory for Xiangqi-specific network."""
	config = NetworkConfig(
		input_channels=15,
		board_height=10,
		board_width=9,
		action_size=8100,
		hidden_channels=64,
		num_res_blocks=3
	)
	return PolicyValueNet(config)


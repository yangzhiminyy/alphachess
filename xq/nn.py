from __future__ import annotations

from typing import Tuple, List

import torch
import torch.nn as nn
import torch.nn.functional as F

from . import constants as C

# Import generic framework
try:
	from alphazero.network import PolicyValueNet, NetworkConfig, create_xiangqi_net
	_HAS_GENERIC = True
except ImportError:
	_HAS_GENERIC = False


def state_to_tensor(state, history_k: int = 1) -> torch.Tensor:
	"""Convert GameState to input tensor of shape [C,H,W] where H=10, W=9.
	Currently uses 15 planes (14 pieces + 1 side-to-move). History stacking is stubbed (k=1).
	"""
	planes = state.to_planes()  # 15 x 90
	h = C.RANKS
	w = C.FILES
	# reshape to [C, H, W] with row-major ranks
	ch = len(planes)
	t = torch.zeros((ch, h, w), dtype=torch.float32)
	for c in range(ch):
		for idx, v in enumerate(planes[c]):
			r = C.rank_of(idx)
			f = C.file_of(idx)
			t[c, r, f] = float(v)
	return t


class XQNet(nn.Module):
	"""Simple CNN policy-value net for 9x10 Xiangqi.
	Policy head outputs 8100 logits (from-to), value head outputs scalar in [-1,1].
	
	This is the legacy implementation. For new code, use create_xiangqi_net() from alphazero.network.
	"""

	def __init__(self, in_channels: int = 15, channels: int = 64, num_blocks: int = 3) -> None:
		super().__init__()
		self.stem = nn.Conv2d(in_channels, channels, kernel_size=3, padding=1)
		self.blocks = nn.ModuleList([
			ResidualBlock(channels) for _ in range(num_blocks)
		])
		# Policy head
		self.p_conv = nn.Conv2d(channels, 32, kernel_size=1)
		self.p_fc = nn.Linear(32 * C.RANKS * C.FILES, C.NUM_SQUARES * C.NUM_SQUARES)
		# Value head
		self.v_conv = nn.Conv2d(channels, 32, kernel_size=1)
		self.v_fc1 = nn.Linear(32 * C.RANKS * C.FILES, 128)
		self.v_fc2 = nn.Linear(128, 1)

	def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
		x = F.relu(self.stem(x))
		for blk in self.blocks:
			x = blk(x)
		# Policy
		p = F.relu(self.p_conv(x))
		p = p.view(p.size(0), -1)
		p = self.p_fc(p)
		# Value
		v = F.relu(self.v_conv(x))
		v = v.view(v.size(0), -1)
		v = F.relu(self.v_fc1(v))
		v = torch.tanh(self.v_fc2(v))
		return p, v.squeeze(-1)


class ResidualBlock(nn.Module):
	def __init__(self, channels: int) -> None:
		super().__init__()
		self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
		self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		res = x
		x = F.relu(self.conv1(x))
		x = self.conv2(x)
		x = F.relu(x + res)
		return x


@torch.no_grad()
def infer_policy_value(model: XQNet, states: List) -> Tuple[List[List[float]], List[float]]:
	model.eval()
	device = next(model.parameters()).device
	inputs = torch.stack([state_to_tensor(s) for s in states]).to(device)
	logits, values = model(inputs)
	policies: List[List[float]] = []
	for i in range(logits.size(0)):
		p = torch.softmax(logits[i], dim=-1).detach().cpu().tolist()
		policies.append(p)
	vals = values.detach().cpu().tolist()
	return policies, vals



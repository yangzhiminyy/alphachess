from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Any

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from .network import PolicyValueNet


@dataclass
class TrainerConfig:
	lr: float = 1e-3
	batch_size: int = 32
	epochs: int = 10
	weight_decay: float = 1e-4


class AlphaZeroDataset(Dataset):
	"""Generic dataset for (state_tensor, policy_target, value_target) tuples."""
	
	def __init__(self, samples: List[Tuple[Any, List[float], float]]):
		"""samples: [(state_tensor_np, pi, z)]"""
		self.samples = samples
	
	def __len__(self):
		return len(self.samples)
	
	def __getitem__(self, idx):
		state_np, pi, z = self.samples[idx]
		state_t = torch.from_numpy(state_np).float()
		pi_t = torch.tensor(pi, dtype=torch.float32)
		z_t = torch.tensor(z, dtype=torch.float32)
		return state_t, pi_t, z_t


class Trainer:
	"""Generic trainer for PolicyValueNet."""
	
	def __init__(self, model: PolicyValueNet, config: TrainerConfig, device: str = "cpu"):
		self.model = model.to(device)
		self.config = config
		self.device = device
		self.optimizer = optim.Adam(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
		self.criterion_policy = nn.CrossEntropyLoss()
		self.criterion_value = nn.MSELoss()
	
	def train_step(self, samples: List[Tuple[Any, List[float], float]]) -> float:
		"""Train on a batch of samples. Returns average loss."""
		if not samples:
			return 0.0
		
		dataset = AlphaZeroDataset(samples)
		loader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=True)
		
		self.model.train()
		total_loss = 0.0
		num_batches = 0
		
		for epoch in range(self.config.epochs):
			for state_batch, pi_batch, z_batch in loader:
				state_batch = state_batch.to(self.device)
				pi_batch = pi_batch.to(self.device)
				z_batch = z_batch.to(self.device)
				
				self.optimizer.zero_grad()
				logits, v = self.model(state_batch)
				
				loss_p = self.criterion_policy(logits, pi_batch)
				loss_v = self.criterion_value(v, z_batch)
				loss = loss_p + loss_v
				
				loss.backward()
				self.optimizer.step()
				
				total_loss += loss.item()
				num_batches += 1
		
		return total_loss / max(1, num_batches)
	
	def save(self, path: str) -> None:
		torch.save(self.model.state_dict(), path)
	
	def load(self, path: str) -> None:
		self.model.load_state_dict(torch.load(path, map_location=self.device))


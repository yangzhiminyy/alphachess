from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Callable

from .selfplay import SelfPlayConfig, self_play_game, save_jsonl


@dataclass
class TrainLoopConfig:
	games_per_batch: int = 10
	sims_per_move: int = 100
	max_moves: int = 150
	train_epochs: int = 3
	train_batch_size: int = 32
	train_lr: float = 1e-3
	max_iterations: int = 100
	model_path: str = "models/latest.pt"
	data_dir: str = "data"
	use_nn: bool = False  # if true, use mcts_nn; else mcts


@dataclass
class TrainLoopStatus:
	running: bool = False
	iteration: int = 0
	games_played: int = 0
	samples_collected: int = 0
	last_train_loss: float = 0.0
	current_model: str = ""
	message: str = ""
	
	def to_dict(self):
		return {
			"running": self.running,
			"iteration": self.iteration,
			"games_played": self.games_played,
			"samples_collected": self.samples_collected,
			"last_train_loss": self.last_train_loss,
			"current_model": self.current_model,
			"message": self.message,
		}


_global_status = TrainLoopStatus()
_stop_requested = False


def get_status() -> TrainLoopStatus:
	return _global_status


def request_stop() -> None:
	global _stop_requested
	_stop_requested = True


def train_loop_iteration(config: TrainLoopConfig, status_callback: Optional[Callable[[str], None]] = None) -> bool:
	"""Run one iteration: self-play -> train -> save.
	Returns True if should continue, False if stopped.
	"""
	global _global_status, _stop_requested
	
	if _stop_requested:
		_global_status.message = "已停止"
		_global_status.running = False
		return False
	
	# Step 1: Self-play
	os.makedirs(config.data_dir, exist_ok=True)
	timestamp = time.strftime("%Y%m%d_%H%M%S")
	jsonl_path = os.path.join(config.data_dir, f"sp_{timestamp}.jsonl")
	
	_global_status.message = f"自对弈中 ({config.games_per_batch} 局)..."
	if status_callback:
		status_callback(_global_status.message)
	
	sp_config = SelfPlayConfig(
		engine="mcts_nn" if config.use_nn else "mcts",
		sims=config.sims_per_move,
		max_moves=config.max_moves,
		model_path=config.model_path if config.use_nn else None,
		store_planes=True,
		store_pi=True,
	)
	
	games = []
	for i in range(config.games_per_batch):
		if _stop_requested:
			_global_status.message = "已停止"
			_global_status.running = False
			return False
		g = self_play_game(sp_config)
		games.append(g)
		_global_status.games_played += 1
		_global_status.samples_collected += len(g['records'])
	
	save_jsonl(jsonl_path, games)
	_global_status.message = f"已保存 {jsonl_path}"
	if status_callback:
		status_callback(_global_status.message)
	
	# Step 2: Train
	if _stop_requested:
		_global_status.message = "已停止"
		_global_status.running = False
		return False
	
	_global_status.message = f"训练中 ({config.train_epochs} epochs)..."
	if status_callback:
		status_callback(_global_status.message)
	
	try:
		from .nn import XQNet
		import torch
		import torch.nn as nn
		import torch.optim as optim
		from torch.utils.data import Dataset, DataLoader
		import json
		from . import constants as C
		
		# Load data
		records = []
		with open(jsonl_path, 'r', encoding='utf-8') as f:
			for line in f:
				game = json.loads(line.strip())
				records.extend(game.get('records', []))
		
		if not records:
			_global_status.message = "无训练数据"
			return True
		
		# Dataset
		class XQDataset(Dataset):
			def __init__(self, recs):
				self.records = recs
			
			def __len__(self):
				return len(self.records)
			
			def __getitem__(self, idx):
				rec = self.records[idx]
				planes = rec['planes']
				pi = rec.get('pi', {})
				z = rec['z']
				tensor_planes = torch.zeros((15, C.RANKS, C.FILES), dtype=torch.float32)
				for c in range(15):
					for sq in range(C.NUM_SQUARES):
						r = C.rank_of(sq)
						f = C.file_of(sq)
						tensor_planes[c, r, f] = float(planes[c][sq])
				pi_tensor = torch.zeros(C.NUM_SQUARES * C.NUM_SQUARES, dtype=torch.float32)
				for k, v in pi.items():
					pi_tensor[int(k)] = float(v)
				z_tensor = torch.tensor(float(z), dtype=torch.float32)
				return tensor_planes, pi_tensor, z_tensor
		
		dataset = XQDataset(records)
		loader = DataLoader(dataset, batch_size=config.train_batch_size, shuffle=True)
		
		device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
		model = XQNet().to(device)
		
		# Resume from existing model
		if os.path.exists(config.model_path):
			model.load_state_dict(torch.load(config.model_path, map_location=device))
		
		optimizer = optim.Adam(model.parameters(), lr=config.train_lr, weight_decay=1e-4)
		criterion_policy = nn.CrossEntropyLoss()
		criterion_value = nn.MSELoss()
		
		total_loss = 0.0
		for epoch in range(config.train_epochs):
			if _stop_requested:
				break
			model.train()
			for planes, pi_target, z_target in loader:
				planes = planes.to(device)
				pi_target = pi_target.to(device)
				z_target = z_target.to(device)
				
				optimizer.zero_grad()
				logits, v = model(planes)
				loss_p = criterion_policy(logits, pi_target)
				loss_v = criterion_value(v, z_target)
				loss = loss_p + loss_v
				loss.backward()
				optimizer.step()
				total_loss += loss.item()
		
		avg_loss = total_loss / (len(loader) * config.train_epochs) if len(loader) > 0 else 0.0
		_global_status.last_train_loss = avg_loss
		
		# Save model
		os.makedirs(os.path.dirname(config.model_path) or ".", exist_ok=True)
		torch.save(model.state_dict(), config.model_path)
		_global_status.current_model = config.model_path
		_global_status.message = f"模型已保存，损失: {avg_loss:.4f}"
		if status_callback:
			status_callback(_global_status.message)
		
	except Exception as e:
		_global_status.message = f"训练错误: {str(e)}"
		if status_callback:
			status_callback(_global_status.message)
	
	_global_status.iteration += 1
	return not _stop_requested


def run_train_loop(config: TrainLoopConfig, status_callback: Optional[Callable[[str], None]] = None) -> None:
	"""Run the full training loop (blocking). Call in a background thread/task."""
	global _global_status, _stop_requested
	_stop_requested = False
	_global_status = TrainLoopStatus(running=True, current_model=config.model_path)
	
	for i in range(config.max_iterations):
		if not train_loop_iteration(config, status_callback):
			break
	
	_global_status.running = False
	_global_status.message = "训练循环结束"
	if status_callback:
		status_callback(_global_status.message)


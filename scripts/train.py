#!/usr/bin/env python3
"""
Legacy training script for XQNet.
For new projects, consider using train_generic.py which supports the modular AlphaZero framework.
"""

import argparse
import json
import os
import sys
from typing import List, Dict

# Add parent directory to path so we can import xq
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from xq.nn import XQNet
from xq import constants as C


class XQDataset(Dataset):
	def __init__(self, records: List[Dict]):
		self.records = records

	def __len__(self):
		return len(self.records)

	def __getitem__(self, idx):
		rec = self.records[idx]
		# planes: 15 x 90
		planes = rec['planes']
		pi = rec.get('pi', {})
		z = rec['z']
		# Convert planes to tensor [15, 10, 9]
		tensor_planes = torch.zeros((15, C.RANKS, C.FILES), dtype=torch.float32)
		for c in range(15):
			for sq in range(C.NUM_SQUARES):
				r = C.rank_of(sq)
				f = C.file_of(sq)
				tensor_planes[c, r, f] = float(planes[c][sq])
		# Convert pi dict to dense array
		pi_tensor = torch.zeros(C.NUM_SQUARES * C.NUM_SQUARES, dtype=torch.float32)
		for k, v in pi.items():
			pi_tensor[int(k)] = float(v)
		z_tensor = torch.tensor(float(z), dtype=torch.float32)
		return tensor_planes, pi_tensor, z_tensor


def load_jsonl(path: str) -> List[Dict]:
	records = []
	with open(path, 'r', encoding='utf-8') as f:
		for line in f:
			game = json.loads(line.strip())
			records.extend(game.get('records', []))
	return records


def main():
	parser = argparse.ArgumentParser(description="Train XQNet on self-play data")
	parser.add_argument("--data", required=True, help="Path to selfplay JSONL")
	parser.add_argument("--model_out", default="models/latest.pt", help="Output model path")
	parser.add_argument("--epochs", type=int, default=10)
	parser.add_argument("--batch_size", type=int, default=32)
	parser.add_argument("--lr", type=float, default=1e-3)
	parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
	args = parser.parse_args()

	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	print(f"Using device: {device}")

	records = load_jsonl(args.data)
	print(f"Loaded {len(records)} training samples")
	if not records:
		print("No data to train on!")
		return

	dataset = XQDataset(records)
	loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

	model = XQNet().to(device)
	if args.resume and os.path.exists(args.resume):
		print(f"Resuming from {args.resume}")
		model.load_state_dict(torch.load(args.resume, map_location=device))

	optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
	criterion_policy = nn.CrossEntropyLoss()
	criterion_value = nn.MSELoss()

	for epoch in range(args.epochs):
		model.train()
		total_loss = 0.0
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

		avg_loss = total_loss / len(loader)
		print(f"Epoch {epoch+1}/{args.epochs} - Loss: {avg_loss:.4f}")

	os.makedirs(os.path.dirname(args.model_out) or ".", exist_ok=True)
	torch.save(model.state_dict(), args.model_out)
	print(f"Model saved to {args.model_out}")


if __name__ == "__main__":
	main()


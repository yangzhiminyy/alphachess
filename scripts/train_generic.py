#!/usr/bin/env python3
"""
Generic training script using the new AlphaZero framework.
Supports training for any game that implements GameInterface.
"""

import argparse
import json
import os
import sys
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from torch.utils.data import DataLoader

from alphazero import Trainer, TrainerConfig, AlphaZeroDataset, create_xiangqi_net
from xq.game_adapter import XiangqiGame


def load_jsonl(path: str) -> List[Dict]:
	"""Load self-play records from JSONL file."""
	records = []
	with open(path, 'r', encoding='utf-8') as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			game = json.loads(line)
			records.extend(game.get('records', []))
	return records


def main():
	parser = argparse.ArgumentParser(description="Train with generic AlphaZero framework")
	parser.add_argument("--game", default="xiangqi", choices=["xiangqi"], 
	                    help="Game to train (currently only xiangqi)")
	parser.add_argument("--data", required=True, help="Path to selfplay JSONL")
	parser.add_argument("--model_out", default="models/generic_latest.pt", help="Output model path")
	parser.add_argument("--epochs", type=int, default=10)
	parser.add_argument("--batch_size", type=int, default=32)
	parser.add_argument("--lr", type=float, default=1e-3)
	parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
	args = parser.parse_args()

	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	print(f"Using device: {device}")
	print(f"Training game: {args.game}")

	# Initialize game
	if args.game == "xiangqi":
		game = XiangqiGame()
		model = create_xiangqi_net().to(device)
	else:
		raise ValueError(f"Unknown game: {args.game}")

	# Load data
	records = load_jsonl(args.data)
	print(f"Loaded {len(records)} training samples")
	if not records:
		print("No data to train on!")
		return

	# Create dataset and dataloader
	dataset = AlphaZeroDataset(records, game)
	loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

	# Create trainer
	config = TrainerConfig(
		learning_rate=args.lr,
		weight_decay=1e-4,
		policy_loss_weight=1.0,
		value_loss_weight=1.0
	)
	trainer = Trainer(model, config, device=device)

	# Resume from checkpoint if specified
	if args.resume and os.path.exists(args.resume):
		print(f"Resuming from {args.resume}")
		trainer.load(args.resume)

	# Training loop
	print(f"Starting training for {args.epochs} epochs...")
	for epoch in range(args.epochs):
		model.train()
		total_loss = 0.0
		total_p_loss = 0.0
		total_v_loss = 0.0
		
		for batch_idx, (states, pi_targets, z_targets) in enumerate(loader):
			states = states.to(device)
			pi_targets = pi_targets.to(device)
			z_targets = z_targets.to(device)

			loss, p_loss, v_loss = trainer.train_step(states, pi_targets, z_targets)
			
			total_loss += loss
			total_p_loss += p_loss
			total_v_loss += v_loss

		avg_loss = total_loss / len(loader)
		avg_p_loss = total_p_loss / len(loader)
		avg_v_loss = total_v_loss / len(loader)
		
		print(f"Epoch {epoch+1}/{args.epochs} - "
		      f"Loss: {avg_loss:.4f} (Policy: {avg_p_loss:.4f}, Value: {avg_v_loss:.4f})")

	# Save model
	os.makedirs(os.path.dirname(args.model_out) or ".", exist_ok=True)
	trainer.save(args.model_out)
	print(f"Model saved to {args.model_out}")


if __name__ == "__main__":
	main()


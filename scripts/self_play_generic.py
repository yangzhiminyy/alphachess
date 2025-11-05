#!/usr/bin/env python3
"""
Generic self-play script using the new AlphaZero framework.
Supports self-play for any game that implements GameInterface.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from alphazero import GenericMCTS, create_xiangqi_net
from xq.game_adapter import XiangqiGame


def self_play_game_generic(game_interface, mcts, max_moves: int = 200, temperature: float = 1.0):
	"""
	Run a single self-play game using the generic framework.
	Returns a list of (state_tensor, policy, outcome) tuples.
	"""
	state = game_interface.get_initial_state()
	game_states = []
	move_count = 0
	
	while move_count < max_moves:
		result = game_interface.get_game_result(state)
		if result is not None:
			break
		
		# Run MCTS
		action_probs = mcts.search(state, temperature=temperature)
		
		# Store state tensor and policy
		state_tensor = game_interface.state_to_tensor(state)
		game_states.append({
			'state': state_tensor,
			'policy': action_probs,
			'player': game_interface.get_current_player(state)
		})
		
		# Sample action
		actions = list(action_probs.keys())
		probs = list(action_probs.values())
		import random
		action = random.choices(actions, weights=probs, k=1)[0]
		
		# Apply action
		state = game_interface.get_next_state(state, action)
		move_count += 1
	
	# Get final result
	result = game_interface.get_game_result(state)
	if result is None:
		result = 0.0  # Draw if max moves reached
	
	# Create training records
	records = []
	for item in game_states:
		# Convert policy dict to list format expected by dataset
		policy_list = [0.0] * game_interface.get_action_size()
		for action, prob in item['policy'].items():
			policy_list[action] = prob
		
		# Convert state tensor to planes format
		planes = item['state'].numpy().tolist()
		
		# Assign outcome from perspective of the player who made the move
		player = item['player']
		if result == 0:
			z = 0.0  # Draw
		elif result == player:
			z = 1.0  # Win
		else:
			z = -1.0  # Loss
		
		records.append({
			'planes': planes,
			'pi': {str(i): p for i, p in enumerate(policy_list) if p > 0},
			'z': z
		})
	
	return records, result


def main():
	parser = argparse.ArgumentParser(description="Generic self-play using AlphaZero framework")
	parser.add_argument("--game", default="xiangqi", choices=["xiangqi"],
	                    help="Game to play (currently only xiangqi)")
	parser.add_argument("--games", type=int, default=10, help="Number of games to play")
	parser.add_argument("--sims", type=int, default=100, help="MCTS simulations per move")
	parser.add_argument("--max_moves", type=int, default=200, help="Max moves per game")
	parser.add_argument("--temperature", type=float, default=1.0, help="Sampling temperature")
	parser.add_argument("--model", type=str, default=None, help="Path to trained model (optional)")
	parser.add_argument("--out", default="selfplay_generic.jsonl", help="Output JSONL file")
	args = parser.parse_args()

	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	print(f"Using device: {device}")
	print(f"Game: {args.game}")

	# Initialize game
	if args.game == "xiangqi":
		game = XiangqiGame()
	else:
		raise ValueError(f"Unknown game: {args.game}")

	# Initialize model and MCTS
	if args.model and os.path.exists(args.model):
		print(f"Loading model from {args.model}")
		model = create_xiangqi_net().to(device)
		model.load_state_dict(torch.load(args.model, map_location=device))
		model.eval()
		
		def policy_fn(state):
			"""Policy function using the trained model."""
			state_tensor = game.state_to_tensor(state).unsqueeze(0).to(device)
			with torch.no_grad():
				logits, value = model(state_tensor)
			probs = torch.softmax(logits[0], dim=0).cpu().numpy()
			return probs.tolist(), float(value[0].cpu().item())
	else:
		print("No model provided, using random policy")
		def policy_fn(state):
			"""Random policy fallback."""
			import numpy as np
			action_size = game.get_action_size()
			probs = np.ones(action_size) / action_size
			return probs.tolist(), 0.0

	mcts = GenericMCTS(game, policy_fn, num_simulations=args.sims, c_puct=1.0)

	# Create output directory
	os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

	# Run self-play games
	all_records = []
	print(f"Starting {args.games} self-play games...")
	
	for game_idx in range(args.games):
		print(f"Game {game_idx + 1}/{args.games}...", end=" ", flush=True)
		records, result = self_play_game_generic(
			game, mcts, 
			max_moves=args.max_moves,
			temperature=args.temperature
		)
		
		result_str = "Draw" if result == 0 else ("Red wins" if result == 1 else "Black wins")
		print(f"{len(records)} moves, Result: {result_str}")
		
		all_records.append({
			'game_id': game_idx,
			'result': result,
			'records': records,
			'timestamp': datetime.now().isoformat()
		})

	# Save to JSONL
	with open(args.out, 'w', encoding='utf-8') as f:
		for game_data in all_records:
			f.write(json.dumps(game_data) + '\n')
	
	print(f"\nSaved {args.games} games ({sum(len(g['records']) for g in all_records)} positions) to {args.out}")


if __name__ == "__main__":
	main()


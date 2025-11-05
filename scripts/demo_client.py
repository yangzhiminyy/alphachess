import argparse
import json
import sys
import os
from typing import Any, Dict

# Add parent directory to path (not strictly needed for demo_client but for consistency)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests


def pretty(obj: Any) -> str:
	return json.dumps(obj, ensure_ascii=False, indent=2)


def main() -> None:
	parser = argparse.ArgumentParser(description="Demo client for Xiangqi API")
	parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL of the server")
	parser.add_argument("--engine", default="ab", choices=["ab", "mcts"], help="Engine to query for best move")
	parser.add_argument("--depth", type=int, default=3, help="Depth for alpha-beta")
	parser.add_argument("--sims", type=int, default=200, help="Simulations for MCTS")
	parser.add_argument("--tau", type=float, default=1.0, help="Temperature for MCTS action probs")
	args = parser.parse_args()

	base = args.base.rstrip("/")
	# Create game
	r = requests.post(f"{base}/api/games", json={})
	r.raise_for_status()
	game = r.json()
	gid = game["game_id"]
	print("Created game:")
	print(pretty(game))

	# Get legal moves
	r = requests.get(f"{base}/api/games/{gid}/legal-moves")
	r.raise_for_status()
	print("\nLegal moves:")
	print(pretty(r.json()))

	# Query best move
	params: Dict[str, Any] = {"engine": args.engine}
	if args.engine == "ab":
		params["depth"] = args.depth
	else:
		params["sims"] = args.sims
		params["tau"] = args.tau
	r = requests.get(f"{base}/api/games/{gid}/best-move", params=params)
	r.raise_for_status()
	best = r.json()
	print("\nBest move:")
	print(pretty(best))

	# If there is a move, play it
	best_move = best.get("best")
	if best_move is not None:
		mv_body = {"move_id": best_move["move_id"]}
		r = requests.post(f"{base}/api/games/{gid}/move", json=mv_body)
		r.raise_for_status()
		print("\nAfter move:")
		print(pretty(r.json()))

	# Show policy mask (length 8100)
	r = requests.get(f"{base}/api/games/{gid}/policy-mask")
	r.raise_for_status()
	mask = r.json()
	print("\nPolicy mask size:", len(mask.get("mask", [])))


if __name__ == "__main__":
	try:
		main()
	except requests.HTTPError as e:
		print("HTTP error:", e, file=sys.stderr)
		raise



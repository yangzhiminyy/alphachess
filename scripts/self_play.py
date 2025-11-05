import argparse
import json
import os
import sys
from typing import List

# Add parent directory to path so we can import xq
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xq.selfplay import SelfPlayConfig, self_play_game, save_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate self-play games using MCTS/MCTS+NN")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--engine", default="mcts", choices=["mcts", "mcts_nn"])
    parser.add_argument("--sims", type=int, default=100)
    parser.add_argument("--max_moves", type=int, default=150)
    parser.add_argument("--tau_moves", type=int, default=10)
    parser.add_argument("--tau_start", type=float, default=1.0)
    parser.add_argument("--tau_final", type=float, default=0.05)
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--out", type=str, default="selfplay.jsonl")
    args = parser.parse_args()

    cfg = SelfPlayConfig(
        engine=args.engine,
        sims=args.sims,
        max_moves=args.max_moves,
        tau_moves=args.tau_moves,
        tau_start=args.tau_start,
        tau_final=args.tau_final,
        model_path=args.model_path,
    )

    # Create output directory if needed
    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    
    games: List[dict] = []
    for i in range(args.games):
        print(f"Playing game {i+1}/{args.games}...")
        g = self_play_game(cfg)
        games.append(g)
        print(f"  Result: {g['result']} ({len(g['records'])} positions)")

    save_jsonl(args.out, games)
    print(f"Saved {len(games)} games to {args.out}")


if __name__ == "__main__":
    main()



from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from . import constants as C
from .state import GameState
from .mcts import MCTS
from .policy import legal_move_mask


PolicyFn = Callable[[GameState], Tuple[List[float], float]]


def default_policy_fn() -> PolicyFn:
	def _pf(state: GameState) -> Tuple[List[float], float]:
		mask = legal_move_mask(state)
		legal_count = sum(1 for x in mask if x > 0)
		p = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
		if legal_count > 0:
			w = 1.0 / legal_count
			for i, v in enumerate(mask):
				if v > 0:
					p[i] = w
		# simple material value
		score = 0
		weights = {
			C.PT_PAWN: 100,
			C.PT_CANNON: 450,
			C.PT_KNIGHT: 450,
			C.PT_BISHOP: 250,
			C.PT_ADVISOR: 250,
			C.PT_ROOK: 900,
			C.PT_KING: 10000,
		}
		for pce in state.board:
			if pce == 0:
				continue
			v = weights[C.piece_type(pce)]
			score += v if pce > 0 else -v
		pov = score if state.side_to_move == C.RED else -score
		val = math.tanh(pov / 2000.0)
		return p, float(val)

	return _pf


@dataclass
class SelfPlayConfig:
	engine: str = "mcts"  # "mcts" or "mcts_nn"
	sims: int = 200
	max_moves: int = 512
	tau_moves: int = 10  # use high temperature for first N moves
	tau_start: float = 1.0
	tau_final: float = 0.05
	resign_threshold: Optional[float] = None  # not used in baseline
	model_path: Optional[str] = None
	# payload size controls
	store_planes: bool = True
	store_pi: bool = True


def _select_with_temperature(probs: Dict[int, float], tau: float) -> int:
	if tau <= 1e-6:
		return max(probs.items(), key=lambda kv: kv[1])[0]
	# convert to weights^ (1/tau)
	weights = {k: (v ** (1.0 / tau)) for k, v in probs.items()}
	s = sum(weights.values())
	if s <= 0:
		return random.choice(list(probs.keys()))
	keys = list(weights.keys())
	ws = [weights[k] / s for k in keys]
	return random.choices(keys, weights=ws, k=1)[0]


def _result_value(state: GameState) -> int:
	res = state.adjudicate_result()
	if res == "red_win":
		return 1
	if res == "black_win":
		return -1
	if res == "draw":
		return 0
	# Ongoing; treat as draw in fallback
	return 0


def self_play_game(config: SelfPlayConfig) -> Dict:
	state = GameState()
	state.setup_starting_position()
	mcts = MCTS()
	# choose policy function
	policy_fn: PolicyFn
	if config.engine == "mcts_nn":
		try:
			from .nn import XQNet, state_to_tensor  # type: ignore
			import torch  # type: ignore
			model = XQNet()
			if config.model_path:
				sd = torch.load(config.model_path, map_location="cpu")
				model.load_state_dict(sd)
			model.eval()

			def _pf(s: GameState):
				with torch.no_grad():
					x = state_to_tensor(s).unsqueeze(0)
					logits, v = model(x)
					policy = torch.softmax(logits[0], dim=-1).tolist()
					return policy, float(v.item())

			policy_fn = _pf
		except Exception:
			policy_fn = default_policy_fn()
	else:
		policy_fn = default_policy_fn()

	records: List[Dict] = []
	moves_san: List[Dict] = []
	for ply in range(config.max_moves):
		root = mcts.run(state, policy_fn, num_simulations=config.sims)
		tau = config.tau_start if ply < config.tau_moves else config.tau_final
		probs = mcts.action_probs(root, tau=tau)
		if not probs:
			break
		# sample move index
		idx = _select_with_temperature(probs, tau)
		from_sq = idx // C.NUM_SQUARES
		to_sq = idx % C.NUM_SQUARES
		# find move object
		move_obj = None
		for cand in state.generate_legal_moves():
			if cand.from_sq == from_sq and cand.to_sq == to_sq:
				move_obj = cand
				break
		if move_obj is None:
			# fallback to argmax
			best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
			from_sq = best_idx // C.NUM_SQUARES
			to_sq = best_idx % C.NUM_SQUARES
			for cand in state.generate_legal_moves():
				if cand.from_sq == from_sq and cand.to_sq == to_sq:
					move_obj = cand
					break
		if move_obj is None:
			break
		# record training sample from current state's POV
		rec = {
			"player": 1 if state.side_to_move == C.RED else -1,
		}
		if config.store_planes:
			rec["planes"] = state.to_planes()
		if config.store_pi:
			rec["pi"] = {str(k): float(v) for k, v in probs.items()}
		records.append(rec)
		moves_san.append({"from": move_obj.from_sq, "to": move_obj.to_sq, "move_id": int(move_obj)})
		state.apply_move(move_obj)
		res = state.adjudicate_result()
		if res is not None:
			break

	# outcome and assign z to each record
	final = _result_value(state)
	for rec in records:
		player = rec["player"]
		rec["z"] = final if player == 1 else -final
		# optionally drop player field
		del rec["player"]

	return {
		"moves": moves_san,
		"result": final,
		"records": records,
	}


def save_jsonl(path: str, games: List[Dict]) -> None:
	with open(path, "w", encoding="utf-8") as f:
		for g in games:
			f.write(json.dumps(g, ensure_ascii=False) + "\n")



from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional, Any

from alphazero.game_interface import GameInterface
from . import constants as C
from .state import GameState
from .move import Move
from .policy import move_index


class XiangqiGame(GameInterface):
	"""Xiangqi adapter implementing GameInterface."""
	
	def __init__(self):
		self.zobrist = None  # shared across all states
	
	def get_initial_state(self) -> GameState:
		s = GameState()
		s.setup_starting_position()
		return s
	
	def get_action_size(self) -> int:
		return C.NUM_SQUARES * C.NUM_SQUARES  # 8100
	
	def get_observation_shape(self) -> Tuple[int, ...]:
		return (15, C.RANKS, C.FILES)  # (C, H, W)
	
	def get_legal_actions(self, state: GameState) -> List[int]:
		moves = state.generate_legal_moves()
		return [move_index(m.from_sq, m.to_sq) for m in moves]
	
	def get_next_state(self, state: GameState, action: int) -> GameState:
		# action is from-to index
		from_sq = action // C.NUM_SQUARES
		to_sq = action % C.NUM_SQUARES
		# Find matching legal move
		for m in state.generate_legal_moves():
			if m.from_sq == from_sq and m.to_sq == to_sq:
				new_state = state.clone()
				new_state.apply_move(m)
				return new_state
		raise ValueError(f"Illegal action {action}")
	
	def get_game_result(self, state: GameState) -> Optional[float]:
		"""Return result from current player's POV."""
		res = state.adjudicate_result()
		if res is None:
			return None
		# Convert to current side's POV
		if res == "draw":
			return 0.0
		if res == "red_win":
			return 1.0 if state.side_to_move == C.RED else -1.0
		if res == "black_win":
			return 1.0 if state.side_to_move == C.BLACK else -1.0
		return 0.0
	
	def get_current_player(self, state: GameState) -> int:
		"""Return current player (RED=1, BLACK=-1)."""
		return state.side_to_move
	
	def state_to_tensor(self, state: GameState) -> np.ndarray:
		"""Return numpy array [C, H, W]."""
		planes = state.to_planes()  # 15 x 90
		tensor = np.zeros((15, C.RANKS, C.FILES), dtype=np.float32)
		for c in range(15):
			for sq in range(C.NUM_SQUARES):
				r = C.rank_of(sq)
				f = C.file_of(sq)
				tensor[c, r, f] = float(planes[c][sq])
		return tensor
	
	def get_canonical_form(self, state: GameState, player: int) -> GameState:
		"""Return state from player's perspective. For Xiangqi, no flip needed (asymmetric)."""
		return state
	
	def get_symmetries(self, state: GameState, pi: List[float]) -> List[Tuple[GameState, List[float]]]:
		"""Xiangqi is asymmetric (palaces differ), so no symmetries by default.
		Could add horizontal flip if handling carefully.
		"""
		return [(state, pi)]
	
	def display(self, state: GameState) -> str:
		"""Return board as string."""
		lines = []
		for r in range(C.RANKS-1, -1, -1):
			row = []
			for f in range(C.FILES):
				p = state.board[C.index_of(f, r)]
				if p == 0:
					row.append('.')
				else:
					pt = C.piece_type(p)
					sym = ['P','C','N','B','A','R','K'][pt-1]
					row.append(sym if p > 0 else sym.lower())
			lines.append(f"{r} " + ' '.join(row))
		lines.append("  " + ' '.join('abcdefghi'))
		return '\n'.join(lines)


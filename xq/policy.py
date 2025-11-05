from __future__ import annotations

from typing import List

from . import constants as C
from .move import Move
from .state import GameState


def move_index(from_sq: int, to_sq: int) -> int:
	"""Map (from,to) in [0..89]x[0..89] to a unique index in [0..8099]."""
	return from_sq * C.NUM_SQUARES + to_sq


def legal_move_mask(state: GameState) -> List[float]:
	"""Return 8100-dim policy mask (0/1 floats) over from-to space.
	Only legal moves are 1. Others are 0.
	"""
	mask = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
	moves = state.generate_legal_moves()
	for m in moves:
		idx = move_index(m.from_sq, m.to_sq)
		mask[idx] = 1.0
	return mask



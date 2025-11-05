from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final, List

from .constants import NUM_SQUARES, NUM_PT


RNG_BITS: Final[int] = 64


def _rand64(rng: random.Random) -> int:
	# Full 64-bit random value
	return rng.getrandbits(RNG_BITS)


@dataclass
class Zobrist:
	"""Zobrist hashing tables and helpers.

	Indices:
	- piece on square: [color_idx(0=RED,1=BLACK)][piece_type 1..7][square 0..89]
	- side to move: one key for BLACK to move (or RED), choose convention
	"""
	pst: List[List[List[int]]]
	side_to_move_key: int

	@staticmethod
	def init(seed: int = 20251031) -> "Zobrist":
		rng = random.Random(seed)
		# pst[color][pt][sq]
		pst: List[List[List[int]]] = [
			[[0] * NUM_SQUARES for _ in range(NUM_PT + 1)],  # RED (index 0)
			[[0] * NUM_SQUARES for _ in range(NUM_PT + 1)],  # BLACK (index 1)
		]
		for color_idx in range(2):
			for pt in range(1, NUM_PT + 1):
				for sq in range(NUM_SQUARES):
					pst[color_idx][pt][sq] = _rand64(rng)
		side_key = _rand64(rng)
		return Zobrist(pst=pst, side_to_move_key=side_key)

	def color_index(self, color: int) -> int:
		# RED -> 0, BLACK -> 1
		return 0 if color > 0 else 1

	def piece_square_key(self, color: int, piece_type: int, square: int) -> int:
		return self.pst[self.color_index(color)][piece_type][square]

	def side_key(self) -> int:
		return self.side_to_move_key



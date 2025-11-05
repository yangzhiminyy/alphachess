from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Tuple


# Board dimensions
FILES: Final[int] = 9
RANKS: Final[int] = 10
NUM_SQUARES: Final[int] = FILES * RANKS  # 90


# Piece type IDs (magnitude encodes type; sign encodes color)
# Keep stable small integers for NN stability and compactness
PT_PAWN: Final[int] = 1  # 兵/卒
PT_CANNON: Final[int] = 2  # 炮
PT_KNIGHT: Final[int] = 3  # 马
PT_BISHOP: Final[int] = 4  # 相/象
PT_ADVISOR: Final[int] = 5  # 仕/士
PT_ROOK: Final[int] = 6  # 车
PT_KING: Final[int] = 7  # 帅/将

PT_MIN: Final[int] = PT_PAWN
PT_MAX: Final[int] = PT_KING
NUM_PT: Final[int] = PT_MAX  # 7, used for indexing 1..7


# Colors: sign convention
RED: Final[int] = 1
BLACK: Final[int] = -1


def make_piece(color: int, piece_type: int) -> int:
	"""Encode a piece as signed small integer: sign=color, magnitude=type.
	0 means empty.
	"""
	return 0 if piece_type == 0 else color * piece_type


def piece_type(piece: int) -> int:
	return abs(piece)


def piece_color(piece: int) -> int:
	return 0 if piece == 0 else (RED if piece > 0 else BLACK)


def is_empty(piece: int) -> bool:
	return piece == 0


# Indexing helpers
def index_of(file: int, rank: int) -> int:
	return rank * FILES + file


def file_of(index: int) -> int:
	return index % FILES


def rank_of(index: int) -> int:
	return index // FILES


# Palace regions (files 3..5), ranks 0..2 for RED palace, 7..9 for BLACK palace
RED_PALACE_FILES: Final[Tuple[int, int]] = (3, 5)
RED_PALACE_RANKS: Final[Tuple[int, int]] = (0, 2)
BLACK_PALACE_FILES: Final[Tuple[int, int]] = (3, 5)
BLACK_PALACE_RANKS: Final[Tuple[int, int]] = (7, 9)


def in_bounds(file: int, rank: int) -> bool:
	return 0 <= file < FILES and 0 <= rank < RANKS


def in_red_palace(file: int, rank: int) -> bool:
	return RED_PALACE_FILES[0] <= file <= RED_PALACE_FILES[1] and (
		RED_PALACE_RANKS[0] <= rank <= RED_PALACE_RANKS[1]
	)


def in_black_palace(file: int, rank: int) -> bool:
	return BLACK_PALACE_FILES[0] <= file <= BLACK_PALACE_FILES[1] and (
		BLACK_PALACE_RANKS[0] <= rank <= BLACK_PALACE_RANKS[1]
	)


def is_across_river(color: int, rank: int) -> bool:
	# River between ranks 4 and 5. RED starts at rank 0 moving +rank; BLACK starts at 9 moving -rank.
	if color == RED:
		return rank >= 5
	else:
		return rank <= 4


@dataclass(frozen=True)
class Direction:
	df: int
	dr: int


# Knight leg offsets: target delta and blocking "leg" offset
KNIGHT_DELTAS: Final[Tuple[Tuple[Direction, Direction], ...]] = (
	# ((target df,dr), (leg df,dr))
	(Direction(1, 2), Direction(0, 1)),
	(Direction(2, 1), Direction(1, 0)),
	(Direction(2, -1), Direction(1, 0)),
	(Direction(1, -2), Direction(0, -1)),
	(Direction(-1, -2), Direction(0, -1)),
	(Direction(-2, -1), Direction(-1, 0)),
	(Direction(-2, 1), Direction(-1, 0)),
	(Direction(-1, 2), Direction(0, 1)),
)


# Bishop (elephant) diagonal steps and eyes (two steps diagonally, eye is the mid-square)
BISHOP_DELTAS: Final[Tuple[Tuple[Direction, Direction], ...]] = (
	(Direction(2, 2), Direction(1, 1)),
	(Direction(2, -2), Direction(1, -1)),
	(Direction(-2, 2), Direction(-1, 1)),
	(Direction(-2, -2), Direction(-1, -1)),
)


# Advisor one-step diagonals within palace
ADVISOR_DELTAS: Final[Tuple[Direction, ...]] = (
	Direction(1, 1),
	Direction(1, -1),
	Direction(-1, 1),
	Direction(-1, -1),
)


# Rook/cannon orthogonal directions
ORTHO_DELTAS: Final[Tuple[Direction, ...]] = (
	Direction(1, 0),
	Direction(-1, 0),
	Direction(0, 1),
	Direction(0, -1),
)



from typing import Final

# Sides
RED: Final[int] = 1
BLACK: Final[int] = -1

# Piece type IDs (absolute codes)
PIECE_NONE: Final[int] = 0
PIECE_PAWN: Final[int] = 1     # 兵/卒
PIECE_CANNON: Final[int] = 2   # 炮
PIECE_KNIGHT: Final[int] = 3   # 马
PIECE_BISHOP: Final[int] = 4   # 相/象
PIECE_ADVISOR: Final[int] = 5  # 仕/士
PIECE_ROOK: Final[int] = 6     # 车
PIECE_KING: Final[int] = 7     # 帅/将

# Move encoding layout (32-bit)
FROM_SHIFT: Final[int] = 0
TO_SHIFT: Final[int] = 7
MOVING_SHIFT: Final[int] = 14
CAPTURED_SHIFT: Final[int] = 18
FLAGS_SHIFT: Final[int] = 22

FROM_MASK: Final[int] = (1 << 7) - 1
TO_MASK: Final[int] = (1 << 7) - 1
TYPE_MASK: Final[int] = (1 << 4) - 1
FLAGS_MASK: Final[int] = (1 << 10) - 1

# Move flags
FLAG_CAPTURE: Final[int] = 1 << 0
FLAG_CHECK: Final[int] = 1 << 1


def pack_move(from_sq: int, to_sq: int, moving_type: int, captured_type: int = 0, flags: int = 0) -> int:
    return ((from_sq & FROM_MASK) << FROM_SHIFT) | \
           ((to_sq & TO_MASK) << TO_SHIFT) | \
           ((moving_type & TYPE_MASK) << MOVING_SHIFT) | \
           ((captured_type & TYPE_MASK) << CAPTURED_SHIFT) | \
           ((flags & FLAGS_MASK) << FLAGS_SHIFT)


def unpack_move(move: int) -> tuple[int, int, int, int, int]:
    from_sq = (move >> FROM_SHIFT) & FROM_MASK
    to_sq = (move >> TO_SHIFT) & TO_MASK
    moving_type = (move >> MOVING_SHIFT) & TYPE_MASK
    captured_type = (move >> CAPTURED_SHIFT) & TYPE_MASK
    flags = (move >> FLAGS_SHIFT) & FLAGS_MASK
    return from_sq, to_sq, moving_type, captured_type, flags


# Material values (decoupled from encoding)
MATERIAL_VALUES: dict[int, int] = {
    PIECE_PAWN: 100,
    PIECE_CANNON: 450,
    PIECE_KNIGHT: 400,
    PIECE_BISHOP: 250,
    PIECE_ADVISOR: 250,
    PIECE_ROOK: 900,
    PIECE_KING: 10000,
}


def piece_index_for_zobrist(piece_code: int) -> int:
    """Map signed piece code to Zobrist index 1..14 (0 unused).
    RED types 1..7 -> 1..7, BLACK types -1..-7 -> 8..14.
    """
    if piece_code == 0:
        return 0
    t = abs(piece_code)
    if piece_code > 0:
        return t  # 1..7
    return 7 + t  # 8..14


def rc_to_sq(row: int, col: int) -> int:
    return row * 9 + col


def sq_to_rc(sq: int) -> tuple[int, int]:
    return divmod(sq, 9)


def in_board(row: int, col: int) -> bool:
    return 0 <= row < 10 and 0 <= col < 9


def in_palace(row: int, col: int, side: int) -> bool:
    if side == RED:
        return 7 <= row <= 9 and 3 <= col <= 5
    return 0 <= row <= 2 and 3 <= col <= 5


def river_row(side: int) -> int:
    return 4 if side == RED else 5



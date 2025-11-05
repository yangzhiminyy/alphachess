from __future__ import annotations

from dataclasses import dataclass
from typing import Final


# Move encoding (32-bit unsigned):
# bits 0..6   : from (0..89)
# bits 7..13  : to (0..89)
# bits 14..17 : moving piece type (1..7) [0 reserved]
# bits 18..21 : captured piece type (0..7)
# bits 22     : is capture flag
# bits 23     : is check flag (optional, best-effort)
# bits 24..27 : hint score (signed nibble via two's complement when used externally)
# bits 28..31 : reserved (extension)

FROM_SHIFT: Final[int] = 0
TO_SHIFT: Final[int] = 7
PT_MOVE_SHIFT: Final[int] = 14
PT_CAPT_SHIFT: Final[int] = 18
CAPTURE_FLAG_SHIFT: Final[int] = 22
CHECK_FLAG_SHIFT: Final[int] = 23
HINT_SHIFT: Final[int] = 24

MASK7: Final[int] = (1 << 7) - 1
MASK4: Final[int] = (1 << 4) - 1


def _pack(from_sq: int, to_sq: int, pt_move: int, pt_captured: int, is_capture: bool, is_check: bool, hint_nibble: int) -> int:
	value = 0
	value |= (from_sq & MASK7) << FROM_SHIFT
	value |= (to_sq & MASK7) << TO_SHIFT
	value |= (pt_move & MASK4) << PT_MOVE_SHIFT
	value |= (pt_captured & MASK4) << PT_CAPT_SHIFT
	if is_capture:
		value |= 1 << CAPTURE_FLAG_SHIFT
	if is_check:
		value |= 1 << CHECK_FLAG_SHIFT
	value |= (hint_nibble & MASK4) << HINT_SHIFT
	return value


@dataclass(frozen=True)
class Move:
	"""Immutable 32-bit move wrapper with helpers."""
	code: int

	@staticmethod
	def make(from_sq: int, to_sq: int, pt_move: int, pt_captured: int = 0, is_check: bool = False, hint_nibble: int = 0) -> "Move":
		return Move(
			_pack(
				from_sq=from_sq,
				to_sq=to_sq,
				pt_move=pt_move,
				pt_captured=pt_captured,
				is_capture=(pt_captured != 0),
				is_check=is_check,
				hint_nibble=hint_nibble,
			)
		)

	@property
	def from_sq(self) -> int:
		return (self.code >> FROM_SHIFT) & MASK7

	@property
	def to_sq(self) -> int:
		return (self.code >> TO_SHIFT) & MASK7

	@property
	def moving_piece_type(self) -> int:
		return (self.code >> PT_MOVE_SHIFT) & MASK4

	@property
	def captured_piece_type(self) -> int:
		return (self.code >> PT_CAPT_SHIFT) & MASK4

	@property
	def is_capture(self) -> bool:
		return ((self.code >> CAPTURE_FLAG_SHIFT) & 1) != 0

	@property
	def is_check(self) -> bool:
		return ((self.code >> CHECK_FLAG_SHIFT) & 1) != 0

	@property
	def hint(self) -> int:
		return (self.code >> HINT_SHIFT) & MASK4

	def with_check_flag(self, is_check: bool) -> "Move":
		if is_check:
			return Move(self.code | (1 << CHECK_FLAG_SHIFT))
		else:
			return Move(self.code & ~(1 << CHECK_FLAG_SHIFT))

	def with_hint(self, hint_nibble: int) -> "Move":
		masked = (self.code & ~(MASK4 << HINT_SHIFT)) | ((hint_nibble & MASK4) << HINT_SHIFT)
		return Move(masked)

	def __int__(self) -> int:  # convenient cast
		return self.code



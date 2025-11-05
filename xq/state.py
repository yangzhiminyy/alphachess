from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Iterable

from . import constants as C
from .move import Move
from .zobrist import Zobrist


@dataclass
class Undo:
	from_sq: int
	to_sq: int
	captured: int
	prev_from_id: int
	prev_to_id: int
	prev_zkey: int
	prev_side: int
	prev_red_king: int
	prev_black_king: int


class GameState:
	"""Board state, move generation, and incremental apply/undo."""

	def __init__(self, board: Optional[List[int]] = None, side_to_move: int = C.RED, zobrist: Optional[Zobrist] = None) -> None:
		self.board: List[int] = [0] * C.NUM_SQUARES if board is None else list(board)
		self.side_to_move: int = side_to_move
		self.zobrist: Zobrist = Zobrist.init() if zobrist is None else zobrist
		self.zkey: int = 0
		self.undo_stack: List[Undo] = []
		self.history: List[int] = []  # Zobrist keys history including current
		self.history_gives_check: List[bool] = []  # whether the move leading to position gave check
		self.history_capture: List[bool] = []  # whether the move leading to position captured a piece
		self.history_chase_pair: List[Optional[tuple[int, int]]] = []  # (chaser_id, target_id) if last move chases exactly one target
		self.ids: List[int] = [0] * C.NUM_SQUARES  # stable piece identities; RED>0, BLACK<0
		# Cache king squares
		self.red_king_sq: int = -1
		self.black_king_sq: int = -1
		self._init_state()

	def _init_state(self) -> None:
		# Compute initial zobrist and king positions; assign piece IDs
		z = 0
		red_id = 1
		black_id = -1
		for sq, p in enumerate(self.board):
			if p != 0:
				z ^= self.zobrist.piece_square_key(C.piece_color(p), C.piece_type(p), sq)
				self.ids[sq] = red_id if p > 0 else black_id
				if p > 0:
					red_id += 1
				else:
					black_id -= 1
				if C.piece_type(p) == C.PT_KING:
					if p > 0:
						self.red_king_sq = sq
					else:
						self.black_king_sq = sq
		if self.side_to_move == C.BLACK:
			z ^= self.zobrist.side_key()
		self.zkey = z
		self.history = [self.zkey]
		self.history_gives_check = [False]
		self.history_capture = [False]
		self.history_chase_pair = [None]

	def clone(self) -> "GameState":
		cl = GameState(self.board, self.side_to_move, self.zobrist)
		# Overwrite computed caches to match exactly
		cl.board = list(self.board)
		cl.ids = list(self.ids)
		cl.zkey = self.zkey
		cl.undo_stack = list(self.undo_stack)
		cl.history = list(self.history)
		cl.history_gives_check = list(self.history_gives_check)
		cl.history_capture = list(self.history_capture)
		cl.history_chase_pair = list(self.history_chase_pair)
		cl.red_king_sq = self.red_king_sq
		cl.black_king_sq = self.black_king_sq
		return cl

	def piece_at(self, sq: int) -> int:
		return self.board[sq]

	def set_piece(self, sq: int, piece: int) -> None:
		self.board[sq] = piece

	def apply_move(self, move: Move) -> None:
		from_sq = move.from_sq
		to_sq = move.to_sq
		moving = self.board[from_sq]
		captured = self.board[to_sq]
		prev = Undo(
			from_sq=from_sq,
			to_sq=to_sq,
			captured=captured,
			prev_from_id=self.ids[from_sq],
			prev_to_id=self.ids[to_sq],
			prev_zkey=self.zkey,
			prev_side=self.side_to_move,
			prev_red_king=self.red_king_sq,
			prev_black_king=self.black_king_sq,
		)
		self.undo_stack.append(prev)
		# Update zkey: remove moving piece from from_sq
		self.zkey ^= self.zobrist.piece_square_key(C.piece_color(moving), C.piece_type(moving), from_sq)
		# Remove captured if any
		if captured != 0:
			self.zkey ^= self.zobrist.piece_square_key(C.piece_color(captured), C.piece_type(captured), to_sq)
		# Move piece and IDs
		self.board[to_sq] = moving
		self.board[from_sq] = 0
		self.ids[to_sq] = self.ids[from_sq]
		self.ids[from_sq] = 0
		# Add moving piece at to_sq
		self.zkey ^= self.zobrist.piece_square_key(C.piece_color(moving), C.piece_type(moving), to_sq)
		# Update king cache
		if C.piece_type(moving) == C.PT_KING:
			if moving > 0:
				self.red_king_sq = to_sq
			else:
				self.black_king_sq = to_sq
		# Flip side
		self.side_to_move = C.RED if self.side_to_move == C.BLACK else C.BLACK
		self.zkey ^= self.zobrist.side_key()
		# Append history with flags for this move
		gave_check = self.is_in_check(self.side_to_move)
		self.history.append(self.zkey)
		self.history_gives_check.append(gave_check)
		self.history_capture.append(captured != 0)
		# Chase pair detection (strict relies on IDs)
		chase_pair = None
		if not gave_check and captured == 0:
			moved_id = self.ids[to_sq]
			moved_pt = C.piece_type(moving)
			moved_color = C.piece_color(moving)
			targets = self._enumerate_capture_targets_for_piece(to_sq, moved_pt, moved_color)
			# Keep only targets that currently have an enemy piece and are attacked by the moved piece
			target_ids = []
			for tsq in targets:
				pid = self.ids[tsq]
				if pid != 0 and ((pid > 0) != (moved_id > 0)):
					target_ids.append(pid)
			if len(target_ids) == 1:
				chase_pair = (moved_id, target_ids[0])
		self.history_chase_pair.append(chase_pair)

	def undo_move(self) -> None:
		prev = self.undo_stack.pop()
		# Restore board
		moving = self.board[prev.to_sq]
		self.board[prev.from_sq] = moving
		self.board[prev.to_sq] = prev.captured
		# Restore IDs
		self.ids[prev.from_sq] = prev.prev_from_id
		self.ids[prev.to_sq] = prev.prev_to_id
		# Restore cached
		self.red_king_sq = prev.prev_red_king
		self.black_king_sq = prev.prev_black_king
		self.side_to_move = prev.prev_side
		self.zkey = prev.prev_zkey
		# Pop current key from history
		if self.history:
			self.history.pop()
			self.history_gives_check.pop()
			self.history_capture.pop()
			self.history_chase_pair.pop()

	def generate_legal_moves(self) -> List[Move]:
		moves = self.generate_pseudo_legal_moves()
		legal: List[Move] = []
		for m in moves:
			self.apply_move(m)
			if (
				not self.is_in_check(-self.side_to_move)
				and not self._is_long_check_forbidden()
				and not (self._is_long_chase_forbidden_strict() or self._is_long_chase_forbidden())
			):
				legal.append(m)
			self.undo_move()
		return legal

	def generate_pseudo_legal_moves(self) -> List[Move]:
		stm = self.side_to_move
		moves: List[Move] = []
		for sq, p in enumerate(self.board):
			if p == 0 or C.piece_color(p) != stm:
				continue
			pt = C.piece_type(p)
			if pt == C.PT_PAWN:
				self._gen_pawn(sq, stm, moves)
			elif pt == C.PT_CANNON:
				self._gen_cannon(sq, stm, moves)
			elif pt == C.PT_KNIGHT:
				self._gen_knight(sq, stm, moves)
			elif pt == C.PT_BISHOP:
				self._gen_bishop(sq, stm, moves)
			elif pt == C.PT_ADVISOR:
				self._gen_advisor(sq, stm, moves)
			elif pt == C.PT_ROOK:
				self._gen_rook(sq, stm, moves)
			elif pt == C.PT_KING:
				self._gen_king(sq, stm, moves)
		return moves

	def is_in_check(self, color: int) -> bool:
		king_sq = self.red_king_sq if color == C.RED else self.black_king_sq
		return self.square_attacked_by(king_sq, -color)

	def square_attacked_by(self, sq: int, attacker_color: int) -> bool:
		# Check rook/king "face", rook, cannon, knight, pawn, advisor, bishop attacks
		f = C.file_of(sq)
		r = C.rank_of(sq)
		# Rook-like and king facing (no screen)
		for d in C.ORTHO_DELTAS:
			ff, rr = f + d.df, r + d.dr
			while C.in_bounds(ff, rr):
				idx = C.index_of(ff, rr)
				p = self.board[idx]
				if p != 0:
					if C.piece_color(p) == attacker_color:
						pt = C.piece_type(p)
						if pt == C.PT_ROOK:
							return True
						if pt == C.PT_KING and ff == f:  # same file unobstructed
							return True
					break
				ff += d.df
				rr += d.dr
		# Cannon: exactly one screen then attacker cannon
		for d in C.ORTHO_DELTAS:
			screen_found = False
			ff, rr = f + d.df, r + d.dr
			while C.in_bounds(ff, rr):
				idx = C.index_of(ff, rr)
				p = self.board[idx]
				if p != 0:
					if not screen_found:
						screen_found = True
					else:
						if C.piece_color(p) == attacker_color and C.piece_type(p) == C.PT_CANNON:
							return True
						break
				ff += d.df
				rr += d.dr
		# Knights
		for (delta, leg) in C.KNIGHT_DELTAS:
			lf, lr = f + leg.df, r + leg.dr
			if not C.in_bounds(lf, lr) or self.board[C.index_of(lf, lr)] != 0:
				continue
			tf, tr = f + delta.df, r + delta.dr
			if not C.in_bounds(tf, tr):
				continue
			p = self.board[C.index_of(tf, tr)]
			if p != 0 and C.piece_color(p) == attacker_color and C.piece_type(p) == C.PT_KNIGHT:
				return True
		# Pawns
		dr = 1 if attacker_color == C.RED else -1
		for df in (0, -1, 1):
			if df == 0:
				# forward only before crossing river; after crossing, sideways attacks count the same squares as moves
				tf, tr = f, r + dr
			else:
				tf, tr = f + df, r
			if not C.in_bounds(tf, tr):
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p != 0 and C.piece_color(p) == attacker_color and C.piece_type(p) == C.PT_PAWN:
				# Ensure sideways only valid after crossing for attacker
				if df != 0:
					if C.is_across_river(attacker_color, C.rank_of(idx)):
						return True
				else:
					return True
		# Advisors (rare to attack king)
		for d in C.ADVISOR_DELTAS:
			tf, tr = f + d.df, r + d.dr
			if not C.in_bounds(tf, tr):
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p != 0 and C.piece_color(p) == attacker_color and C.piece_type(p) == C.PT_ADVISOR:
				# Must be within opponent palace to be valid piece location; assume board is valid
				return True
		# Bishops (elephants) can only attack within own side
		for (delta, eye) in C.BISHOP_DELTAS:
			tf, tr = f + delta.df, r + delta.dr
			mf, mr = f + eye.df, r + eye.dr
			if not C.in_bounds(tf, tr) or not C.in_bounds(mf, mr):
				continue
			if self.board[C.index_of(mf, mr)] != 0:
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p != 0 and C.piece_color(p) == attacker_color and C.piece_type(p) == C.PT_BISHOP:
				# Ensure not across river for bishops
				rank = C.rank_of(idx)
				if attacker_color == C.RED and rank <= 4:
					return True
				if attacker_color == C.BLACK and rank >= 5:
					return True
		return False

	def _push(self, moves: List[Move], from_sq: int, to_sq: int, pt: int) -> None:
		cap = self.board[to_sq]
		moves.append(Move.make(from_sq, to_sq, pt_move=pt, pt_captured=C.piece_type(cap) if cap != 0 else 0))

	def _gen_rook(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_ROOK
		for d in C.ORTHO_DELTAS:
			ff, rr = f + d.df, r + d.dr
			while C.in_bounds(ff, rr):
				idx = C.index_of(ff, rr)
				p = self.board[idx]
				if p == 0:
					self._push(acc, sq, idx, pt)
					ff += d.df
					rr += d.dr
				else:
					if C.piece_color(p) != color:
						self._push(acc, sq, idx, pt)
					break

	def _gen_cannon(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_CANNON
		for d in C.ORTHO_DELTAS:
			# non-capture moves until first block
			ff, rr = f + d.df, r + d.dr
			while C.in_bounds(ff, rr):
				idx = C.index_of(ff, rr)
				p = self.board[idx]
				if p == 0:
					self._push(acc, sq, idx, pt)
					ff += d.df
					rr += d.dr
				else:
					break
			# capture over exactly one screen
			screen_f, screen_r = ff, rr
			ff += d.df
			rr += d.dr
			while C.in_bounds(ff, rr):
				idx = C.index_of(ff, rr)
				p = self.board[idx]
				if p != 0:
					if C.piece_color(p) != color:
						self._push(acc, sq, idx, pt)
					break
				ff += d.df
				rr += d.dr

	def _gen_knight(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_KNIGHT
		for (delta, leg) in C.KNIGHT_DELTAS:
			lf, lr = f + leg.df, r + leg.dr
			if not C.in_bounds(lf, lr) or self.board[C.index_of(lf, lr)] != 0:
				continue
			tf, tr = f + delta.df, r + delta.dr
			if not C.in_bounds(tf, tr):
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p == 0 or C.piece_color(p) != color:
				self._push(acc, sq, idx, pt)

	def _gen_bishop(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_BISHOP
		for (delta, eye) in C.BISHOP_DELTAS:
			mf, mr = f + eye.df, r + eye.dr
			if not C.in_bounds(mf, mr) or self.board[C.index_of(mf, mr)] != 0:
				continue
			tf, tr = f + delta.df, r + delta.dr
			if not C.in_bounds(tf, tr):
				continue
			# must not cross river
			if color == C.RED and tr > 4:
				continue
			if color == C.BLACK and tr < 5:
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p == 0 or C.piece_color(p) != color:
				self._push(acc, sq, idx, pt)

	def _gen_advisor(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_ADVISOR
		for d in C.ADVISOR_DELTAS:
			tf, tr = f + d.df, r + d.dr
			if not C.in_bounds(tf, tr):
				continue
			# must stay within palace
			if color == C.RED and not C.in_red_palace(tf, tr):
				continue
			if color == C.BLACK and not C.in_black_palace(tf, tr):
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p == 0 or C.piece_color(p) != color:
				self._push(acc, sq, idx, pt)

	def _gen_king(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_KING
		for d in C.ORTHO_DELTAS:
			tf, tr = f + d.df, r + d.dr
			if not C.in_bounds(tf, tr):
				continue
			# must stay within own palace
			if color == C.RED and not C.in_red_palace(tf, tr):
				continue
			if color == C.BLACK and not C.in_black_palace(tf, tr):
				continue
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p == 0 or C.piece_color(p) != color:
				# also ensure no "king facing" after move will be handled by legal filter
				self._push(acc, sq, idx, pt)
		# king facing capture (rarely a move but ensure pseudo-legal includes direct facing along file)
		# Regular rook-like move generation already covers stepping; no need to add extra here

	def _gen_pawn(self, sq: int, color: int, acc: List[Move]) -> None:
		f, r = C.file_of(sq), C.rank_of(sq)
		pt = C.PT_PAWN
		dr = 1 if color == C.RED else -1
		# forward
		tf, tr = f, r + dr
		if C.in_bounds(tf, tr):
			idx = C.index_of(tf, tr)
			p = self.board[idx]
			if p == 0 or C.piece_color(p) != color:
				self._push(acc, sq, idx, pt)
		# after crossing river, can move left/right
		if C.is_across_river(color, r):
			for df in (-1, 1):
				tf, tr = f + df, r
				if not C.in_bounds(tf, tr):
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p == 0 or C.piece_color(p) != color:
					self._push(acc, sq, idx, pt)

	def setup_starting_position(self) -> None:
		# Standard Xiangqi start position (RED at ranks 0-4, BLACK at 9-5)
		self.board = [0] * C.NUM_SQUARES
		# RED pieces
		def place(file: int, rank: int, pt: int, color: int) -> None:
			self.board[C.index_of(file, rank)] = C.make_piece(color, pt)
		# Rooks
		place(0, 0, C.PT_ROOK, C.RED)
		place(8, 0, C.PT_ROOK, C.RED)
		# Knights
		place(1, 0, C.PT_KNIGHT, C.RED)
		place(7, 0, C.PT_KNIGHT, C.RED)
		# Bishops
		place(2, 0, C.PT_BISHOP, C.RED)
		place(6, 0, C.PT_BISHOP, C.RED)
		# Advisors
		place(3, 0, C.PT_ADVISOR, C.RED)
		place(5, 0, C.PT_ADVISOR, C.RED)
		# King
		place(4, 0, C.PT_KING, C.RED)
		# Cannons
		place(1, 2, C.PT_CANNON, C.RED)
		place(7, 2, C.PT_CANNON, C.RED)
		# Pawns
		for f in range(0, 9, 2):
			place(f, 3, C.PT_PAWN, C.RED)
		# BLACK pieces
		place(0, 9, C.PT_ROOK, C.BLACK)
		place(8, 9, C.PT_ROOK, C.BLACK)
		place(1, 9, C.PT_KNIGHT, C.BLACK)
		place(7, 9, C.PT_KNIGHT, C.BLACK)
		place(2, 9, C.PT_BISHOP, C.BLACK)
		place(6, 9, C.PT_BISHOP, C.BLACK)
		place(3, 9, C.PT_ADVISOR, C.BLACK)
		place(5, 9, C.PT_ADVISOR, C.BLACK)
		place(4, 9, C.PT_KING, C.BLACK)
		place(1, 7, C.PT_CANNON, C.BLACK)
		place(7, 7, C.PT_CANNON, C.BLACK)
		for f in range(0, 9, 2):
			place(f, 6, C.PT_PAWN, C.BLACK)
		self.side_to_move = C.RED
		self.undo_stack.clear()
		self.red_king_sq = C.index_of(4, 0)
		self.black_king_sq = C.index_of(4, 9)
		self._init_state()

	def threefold_repetition(self) -> bool:
		"""Simple threefold repetition detection on exact Zobrist keys (same side-to-move).
		Counts occurrences of current zkey in history.
		"""
		cur = self.zkey
		count = 0
		for k in self.history:
			if k == cur:
				count += 1
		return count >= 3

	def _is_long_check_forbidden(self) -> bool:
		"""Detects and forbids perpetual check by the side who just moved.
		Assumes this is called immediately after applying a candidate move.
		Heuristic: if the last move gave check, and the current position has
		occurred at least 3 times with a fixed cycle length, with all cycle
		steps being checking moves by the same side and without captures in
		those checking steps, forbid it.
		"""
		# Last move index
		end = len(self.history) - 1
		if end <= 0:
			return False
		if not self.history_gives_check[end]:
			return False
		# Find previous occurrence of current key
		cur = self.history[end]
		prev_idx = -1
		for i in range(end - 1, -1, -1):
			if self.history[i] == cur:
				prev_idx = i
				break
		if prev_idx < 0:
			return False
		step = end - prev_idx
		if step <= 0:
			return False
		# Count cycle repeats
		indices = []
		p = end
		while p >= 0:
			indices.append(p)
			p -= step
		# Need at least 3 occurrences (including current)
		if len(indices) < 3:
			return False
		# All cycle steps must be checking moves by the same side and non-captures
		for idx in indices:
			if not self.history_gives_check[idx]:
				return False
			if self.history_capture[idx]:
				return False
		return True

	def _is_long_chase_forbidden(self) -> bool:
		"""Forbid perpetual non-capture, non-check cycles (approximate 长捉/长打禁手).
		Called after applying a candidate move.
		Logic: if current position repeats with step>=2 and the positions in this
		cycle (same indices pattern as repetition) had no capture and no check, then
		forbid the move that re-enters the cycle.
		"""
		end = len(self.history) - 1
		if end <= 0:
			return False
		# The move leading to current must be non-capture and non-check
		if self.history_capture[end] or self.history_gives_check[end]:
			return False
		cur = self.history[end]
		prev_idx = -1
		for i in range(end - 1, -1, -1):
			if self.history[i] == cur:
				prev_idx = i
				break
		if prev_idx < 0:
			return False
		step = end - prev_idx
		if step < 2:
			return False
		# Build cycle indices and require at least 3 occurrences
		indices = []
		p = end
		while p >= 0:
			indices.append(p)
			p -= step
		if len(indices) < 3:
			return False
		# All in cycle must be non-capture and non-check
		for idx in indices:
			if self.history_capture[idx] or self.history_gives_check[idx]:
				return False
		return True

	def _is_long_chase_forbidden_strict(self) -> bool:
		"""Strict 长捉/长打禁手：检测同一“追子对(chaser_id,target_id)”的循环重复。
		条件：
		- 当前局面与过去某次相同（含行棋方），定义步长 step>=2；
		- 循环中的每次（按同索引差 step 回溯）满足：
		  - 无吃子，非将军；
		  - `history_chase_pair[idx]` 存在，且恒等于同一对 (chaser,target)。
		- 至少出现 3 次。
		"""
		end = len(self.history) - 1
		if end <= 0:
			return False
		cp = self.history_chase_pair[end]
		if cp is None:
			return False
		cur = self.history[end]
		prev_idx = -1
		for i in range(end - 1, -1, -1):
			if self.history[i] == cur:
				prev_idx = i
				break
		if prev_idx < 0:
			return False
		step = end - prev_idx
		if step < 2:
			return False
		indices = []
		p = end
		while p >= 0:
			indices.append(p)
			p -= step
		if len(indices) < 3:
			return False
		for idx in indices:
			if self.history_capture[idx] or self.history_gives_check[idx]:
				return False
			if self.history_chase_pair[idx] != cp:
				return False
		return True

	def _enumerate_capture_targets_for_piece(self, from_sq: int, pt: int, color: int) -> List[int]:
		"""Enumerate enemy-occupied squares that this piece could capture in one move."""
		f, r = C.file_of(from_sq), C.rank_of(from_sq)
		targets: List[int] = []
		if pt == C.PT_ROOK:
			for d in C.ORTHO_DELTAS:
				ff, rr = f + d.df, r + d.dr
				while C.in_bounds(ff, rr):
					idx = C.index_of(ff, rr)
					p = self.board[idx]
					if p != 0:
						if C.piece_color(p) != color:
							targets.append(idx)
						break
					ff += d.df
					rr += d.dr
		elif pt == C.PT_CANNON:
			for d in C.ORTHO_DELTAS:
				ff, rr = f + d.df, r + d.dr
				# find first screen
				while C.in_bounds(ff, rr) and self.board[C.index_of(ff, rr)] == 0:
					ff += d.df
					rr += d.dr
				# now search next piece as potential capture
				ff += d.df
				rr += d.dr
				while C.in_bounds(ff, rr):
					idx = C.index_of(ff, rr)
					p = self.board[idx]
					if p != 0:
						if C.piece_color(p) != color:
							targets.append(idx)
						break
					ff += d.df
					rr += d.dr
		elif pt == C.PT_KNIGHT:
			for (delta, leg) in C.KNIGHT_DELTAS:
				lf, lr = f + leg.df, r + leg.dr
				if not C.in_bounds(lf, lr) or self.board[C.index_of(lf, lr)] != 0:
					continue
				tf, tr = f + delta.df, r + delta.dr
				if not C.in_bounds(tf, tr):
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p != 0 and C.piece_color(p) != color:
					targets.append(idx)
		elif pt == C.PT_BISHOP:
			for (delta, eye) in C.BISHOP_DELTAS:
				mf, mr = f + eye.df, r + eye.dr
				if not C.in_bounds(mf, mr) or self.board[C.index_of(mf, mr)] != 0:
					continue
				tf, tr = f + delta.df, r + delta.dr
				if not C.in_bounds(tf, tr):
					continue
				if color == C.RED and tr > 4:
					continue
				if color == C.BLACK and tr < 5:
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p != 0 and C.piece_color(p) != color:
					targets.append(idx)
		elif pt == C.PT_ADVISOR:
			for d in C.ADVISOR_DELTAS:
				tf, tr = f + d.df, r + d.dr
				if not C.in_bounds(tf, tr):
					continue
				if color == C.RED and not C.in_red_palace(tf, tr):
					continue
				if color == C.BLACK and not C.in_black_palace(tf, tr):
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p != 0 and C.piece_color(p) != color:
					targets.append(idx)
		elif pt == C.PT_KING:
			for d in C.ORTHO_DELTAS:
				tf, tr = f + d.df, r + d.dr
				if not C.in_bounds(tf, tr):
					continue
				if color == C.RED and not C.in_red_palace(tf, tr):
					continue
				if color == C.BLACK and not C.in_black_palace(tf, tr):
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p != 0 and C.piece_color(p) != color:
					targets.append(idx)
			# Note: facing king attack covered by long-check logic; not considered chase
		elif pt == C.PT_PAWN:
			dr = 1 if color == C.RED else -1
			candidate = []
			candidate.append((f, r + dr))
			if C.is_across_river(color, r):
				candidate.append((f - 1, r))
				candidate.append((f + 1, r))
			for tf, tr in candidate:
				if not C.in_bounds(tf, tr):
					continue
				idx = C.index_of(tf, tr)
				p = self.board[idx]
				if p != 0 and C.piece_color(p) != color:
					targets.append(idx)
		return targets

	def is_checkmate(self) -> bool:
		if not self.is_in_check(self.side_to_move):
			return False
		return len(self.generate_legal_moves()) == 0

	def is_stalemate(self) -> bool:
		if self.is_in_check(self.side_to_move):
			return False
		return len(self.generate_legal_moves()) == 0

	def adjudicate_result(self) -> Optional[str]:
		"""Return game result: 'red_win', 'black_win', 'draw', or None if ongoing.
		- King captured means immediate loss
		- Checkmate decides winner
		- Stalemate is draw
		- Threefold repetition is draw
		"""
		# Check if a king is missing (captured)
		red_has_king = any(C.piece_type(p) == C.PT_KING and p > 0 for p in self.board)
		black_has_king = any(C.piece_type(p) == C.PT_KING and p < 0 for p in self.board)
		if not red_has_king:
			return "black_win"
		if not black_has_king:
			return "red_win"
		
		if self.is_checkmate():
			return "black_win" if self.side_to_move == C.RED else "red_win"
		if self.is_stalemate():
			return "draw"
		if self.threefold_repetition():
			return "draw"
		return None

	def to_planes(self) -> List[List[int]]:
		"""Return 15 planes (14 piece planes + 1 side-to-move plane).
		Planes:
		- 0..6: RED PT1..7
		- 7..13: BLACK PT1..7
		- 14: side to move (all 1 if RED to move, else 0)
		"""
		planes = [[0] * C.NUM_SQUARES for _ in range(15)]
		for sq, p in enumerate(self.board):
			if p == 0:
				continue
			pt = C.piece_type(p)
			idx = (pt - 1) if p > 0 else (7 + pt - 1)
			planes[idx][sq] = 1
		if self.side_to_move == C.RED:
			for i in range(C.NUM_SQUARES):
				planes[14][i] = 1
		return planes



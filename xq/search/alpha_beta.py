from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

from ..state import GameState
from ..move import Move
from .. import constants as C


def simple_material_eval(state: GameState) -> int:
	"""Very simple material-only eval as placeholder. Positive favors RED."""
	weights = {
		C.PT_PAWN: 100,
		C.PT_CANNON: 450,
		C.PT_KNIGHT: 450,
		C.PT_BISHOP: 250,
		C.PT_ADVISOR: 250,
		C.PT_ROOK: 900,
		C.PT_KING: 10000,
	}
	red = 0
	black = 0
	for p in state.board:
		if p == 0:
			continue
		v = weights[C.piece_type(p)]
		if p > 0:
			red += v
		else:
			black += v
	return red - black


@dataclass
class TTEntry:
	zkey: int
	depth: int
	flag: int  # 0=EXACT, 1=LOWERBOUND, 2=UPPERBOUND
	score: int
	move: Optional[Move]


class TranspositionTable:
	def __init__(self, size: int = 1 << 20) -> None:
		self.size = size
		self.table: Dict[int, TTEntry] = {}

	def get(self, key: int) -> Optional[TTEntry]:
		return self.table.get(key)

	def put(self, key: int, entry: TTEntry) -> None:
		self.table[key] = entry


def alphabeta_search(state: GameState, depth: int, tt: Optional[TranspositionTable] = None, use_quiescence: bool = True) -> Tuple[Optional[Move], int]:
    """Return best move and score for RED-positive perspective (state.side_to_move POV via negamax)."""
    if tt is None:
        tt = TranspositionTable()
    heur = Heuristics()
    best_move, best_score = _negamax(state, depth, -10_000_000, 10_000_000, tt, heur, 0, use_quiescence)
    return best_move, best_score


def _order_moves(state: GameState, moves: List[Move], heur: "Heuristics", ply: int) -> List[Move]:
    killers = heur.killers[ply] if ply < len(heur.killers) else []
    k1 = killers[0] if killers else None
    k2 = killers[1] if len(killers) > 1 else None
    def key(m: Move) -> Tuple[int, int, int]:
        if m.is_capture:
            # MVV/LVA-ish: captured type first
            return (0, -m.captured_piece_type, -m.moving_piece_type)
        if (k1 is not None and int(m) == k1) or (k2 is not None and int(m) == k2):
            return (1, 0, 0)
        h = heur.history[m.from_sq][m.to_sq]
        return (2, -h, 0)
    return sorted(moves, key=key)


def _negamax(state: GameState, depth: int, alpha: int, beta: int, tt: TranspositionTable, heur: "Heuristics", ply: int, use_qs: bool) -> Tuple[Optional[Move], int]:
	entry = tt.get(state.zkey)
	if entry is not None and entry.depth >= depth:
		if entry.flag == 0:
			return entry.move, entry.score
		elif entry.flag == 1 and entry.score > alpha:
			alpha = entry.score
		elif entry.flag == 2 and entry.score < beta:
			beta = entry.score
		if alpha >= beta:
			return entry.move, entry.score

	if depth == 0:
		if use_qs:
			return None, _qsearch(state, alpha, beta)
		return None, _evaluate(state)

	moves = state.generate_legal_moves()
	if not moves:
		# mate or stalemate
		if state.is_in_check(state.side_to_move):
			return None, -9_999_999 + (3 - depth)
		else:
			return None, 0

	moves = _order_moves(state, moves, heur, ply)
	best_move: Optional[Move] = None
	best_score = -10_000_000
	orig_alpha = alpha
	for m in moves:
		state.apply_move(m)
		_, score = _negamax(state, depth - 1, -beta, -alpha, tt, heur, ply + 1, use_qs)
		state.undo_move()
		score = -score
		if score > best_score:
			best_score = score
			best_move = m
		if score > alpha:
			alpha = score
		if alpha >= beta:
			# Update heuristics on cutoff
			_record_cutoff(heur, m, ply)
			break

	flag = 0
	if best_score <= orig_alpha:
		flag = 2  # upperbound
	elif best_score >= beta:
		flag = 1  # lowerbound
	tt.put(state.zkey, TTEntry(zkey=state.zkey, depth=depth, flag=flag, score=best_score, move=best_move))
	return best_move, best_score


def _evaluate(state: GameState) -> int:
	# POV: side_to_move; convert to RED POV by sign
	score = simple_material_eval(state)
	return score if state.side_to_move == C.RED else -score


class Heuristics:
	def __init__(self, max_ply: int = 128) -> None:
		self.history: List[List[int]] = [[0 for _ in range(C.NUM_SQUARES)] for _ in range(C.NUM_SQUARES)]
		self.killers: List[List[Optional[int]]] = [[None, None] for _ in range(max_ply)]


def _record_cutoff(heur: Heuristics, move: Move, ply: int) -> None:
	# History bonus
	heur.history[move.from_sq][move.to_sq] += 1
	# Killers
	km = heur.killers[ply]
	code = int(move)
	if km[0] != code:
		km[1] = km[0]
		km[0] = code


def _qsearch(state: GameState, alpha: int, beta: int) -> int:
	stand_pat = _evaluate(state)
	if stand_pat >= beta:
		return beta
	if stand_pat > alpha:
		alpha = stand_pat
	# Consider only captures
	moves = state.generate_legal_moves()
	capture_moves = [m for m in moves if m.is_capture]
	# Simple ordering: biggest capture first
	capture_moves.sort(key=lambda m: (-m.captured_piece_type, -m.moving_piece_type))
	for m in capture_moves:
		state.apply_move(m)
		score = -_qsearch(state, -beta, -alpha)
		state.undo_move()
		if score >= beta:
			return beta
		if score > alpha:
			alpha = score
	return alpha



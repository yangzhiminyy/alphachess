"""
Xiangqi (Chinese Chess) core engine package.

Public API (stable):
- constants: piece and board constants
- move: 32-bit move encoding helpers
- zobrist: Zobrist hashing context
- state: GameState with move generation and apply/undo
"""

from . import constants
from .move import Move
from .zobrist import Zobrist
from .state import GameState
from .policy import legal_move_mask
from .search.alpha_beta import alphabeta_search, TranspositionTable
from .mcts import MCTS

__all__ = [
	"constants",
	"Move",
	"Zobrist",
	"GameState",
	"legal_move_mask",
	"alphabeta_search",
	"TranspositionTable",
    "MCTS",
]



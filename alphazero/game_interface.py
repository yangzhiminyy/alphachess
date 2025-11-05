from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any


class GameInterface(ABC):
	"""Abstract interface for any board game to work with AlphaZero framework."""
	
	@abstractmethod
	def get_initial_state(self) -> Any:
		"""Return initial game state."""
		pass
	
	@abstractmethod
	def get_action_size(self) -> int:
		"""Return total number of possible actions (e.g. 8100 for Xiangqi from-to)."""
		pass
	
	@abstractmethod
	def get_observation_shape(self) -> Tuple[int, ...]:
		"""Return shape of observation tensor, e.g. (C, H, W)."""
		pass
	
	@abstractmethod
	def get_legal_actions(self, state: Any) -> List[int]:
		"""Return list of legal action indices."""
		pass
	
	@abstractmethod
	def get_next_state(self, state: Any, action: int) -> Any:
		"""Return new state after applying action."""
		pass
	
	@abstractmethod
	def get_game_result(self, state: Any) -> Optional[float]:
		"""Return game result from current player's POV: 1=win, -1=loss, 0=draw, None=ongoing."""
		pass
	
	@abstractmethod
	def get_current_player(self, state: Any) -> int:
		"""Return current player (e.g. 1 for red, -1 for black)."""
		pass
	
	@abstractmethod
	def state_to_tensor(self, state: Any) -> Any:
		"""Convert state to neural network input tensor (numpy or torch)."""
		pass
	
	@abstractmethod
	def get_canonical_form(self, state: Any, player: int) -> Any:
		"""Return state from current player's perspective (for symmetry)."""
		pass
	
	@abstractmethod
	def get_symmetries(self, state: Any, pi: List[float]) -> List[Tuple[Any, List[float]]]:
		"""Return list of (state, policy) symmetries for data augmentation."""
		pass
	
	@abstractmethod
	def display(self, state: Any) -> str:
		"""Return human-readable string representation of state."""
		pass


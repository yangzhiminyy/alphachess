from __future__ import annotations

import math
import random
from typing import Callable, Dict, Optional, Tuple, List, Any

from .game_interface import GameInterface


PolicyValueFn = Callable[[Any], Tuple[List[float], float]]


class MCTSNode:
	def __init__(self, prior: float) -> None:
		self.prior = prior
		self.visit_count = 0
		self.value_sum = 0.0
		self.children: Dict[int, MCTSNode] = {}
	
	def value(self) -> float:
		return self.value_sum / max(1, self.visit_count)
	
	def uct_score(self, parent_visit: int, cpuct: float) -> float:
		u = cpuct * self.prior * math.sqrt(parent_visit) / (1 + self.visit_count)
		return self.value() + u


class GenericMCTS:
	"""Generic MCTS for any game implementing GameInterface."""
	
	def __init__(self, game: GameInterface, cpuct: float = 1.5, dirichlet_alpha: float = 0.3, dirichlet_frac: float = 0.25):
		self.game = game
		self.cpuct = cpuct
		self.dirichlet_alpha = dirichlet_alpha
		self.dirichlet_frac = dirichlet_frac
	
	def search(self, state: Any, policy_value_fn: PolicyValueFn, num_simulations: int = 200) -> Dict[int, float]:
		"""Run MCTS and return action visit counts."""
		root = MCTSNode(prior=1.0)
		
		for _ in range(num_simulations):
			self._simulate(state, root, policy_value_fn)
		
		# Return visit counts as policy
		total = sum(child.visit_count for child in root.children.values())
		if total == 0:
			return {}
		return {action: child.visit_count / total for action, child in root.children.items()}
	
	def _simulate(self, state: Any, node: MCTSNode, policy_value_fn: PolicyValueFn) -> float:
		# Check terminal
		result = self.game.get_game_result(state)
		if result is not None:
			return result
		
		# Expand if not yet
		if not node.children:
			legal = self.game.get_legal_actions(state)
			if not legal:
				return 0.0
			
			policy, value = policy_value_fn(state)
			
			# Mask and normalize
			legal_probs = {a: policy[a] for a in legal}
			total = sum(legal_probs.values())
			if total > 0:
				legal_probs = {a: p / total for a, p in legal_probs.items()}
			else:
				w = 1.0 / len(legal)
				legal_probs = {a: w for a in legal}
			
			# Add Dirichlet noise at root
			if node.visit_count == 0 and len(legal_probs) > 0:
				noise = _sample_dirichlet(len(legal_probs), self.dirichlet_alpha)
				actions = list(legal_probs.keys())
				for i, a in enumerate(actions):
					legal_probs[a] = (1 - self.dirichlet_frac) * legal_probs[a] + self.dirichlet_frac * noise[i]
			
			# Create children
			for action, prob in legal_probs.items():
				node.children[action] = MCTSNode(prior=prob)
			
			node.visit_count += 1
			node.value_sum += value
			return value
		
		# Select best child
		best_action = max(node.children.items(), key=lambda kv: kv[1].uct_score(node.visit_count, self.cpuct))[0]
		child = node.children[best_action]
		
		# Recurse
		next_state = self.game.get_next_state(state, best_action)
		value = -self._simulate(next_state, child, policy_value_fn)
		
		# Backup
		node.visit_count += 1
		node.value_sum += value
		
		return value


def _sample_dirichlet(k: int, alpha: float) -> List[float]:
	if k <= 0:
		return []
	vals = [random.gammavariate(alpha, 1.0) for _ in range(k)]
	s = sum(vals)
	if s <= 0:
		return [1.0 / k] * k
	return [v / s for v in vals]


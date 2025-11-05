from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple, List

from .state import GameState
from .policy import legal_move_mask, move_index
from .move import Move
from . import constants as C


PolicyFn = Callable[[GameState], Tuple[List[float], float]]  # returns (policy over 8100, value in [-1,1]]


@dataclass
class EdgeStats:
	N: int = 0
	W: float = 0.0
	Q: float = 0.0
	P: float = 0.0


class Node:
	def __init__(self, parent: Optional["Node"], prior: float) -> None:
		self.parent = parent
		self.prior = prior
		self.children: Dict[int, Node] = {}
		self.edges: Dict[int, EdgeStats] = {}
		self.is_expanded: bool = False

	def total_visit(self) -> int:
		return sum(es.N for es in self.edges.values())


class MCTS:
	def __init__(self, cpuct: float = 1.5, dirichlet_alpha: float = 0.3, dirichlet_frac: float = 0.25) -> None:
		self.cpuct = cpuct
		self.dirichlet_alpha = dirichlet_alpha
		self.dirichlet_frac = dirichlet_frac

	def run(self, root_state: GameState, policy_fn: PolicyFn, num_simulations: int = 200, time_limit_s: Optional[float] = None) -> Node:
		root = Node(parent=None, prior=1.0)
		self._expand(root_state, root, policy_fn, add_noise=True)
		start_t = None
		if time_limit_s is not None:
			import time
			start_t = time.perf_counter()
		for _ in range(num_simulations):
			if start_t is not None:
				import time
				if (time.perf_counter() - start_t) >= time_limit_s:
					break
			state = root_state.clone()
			path: List[Tuple[Node, Move, int]] = []  # (node, move, move_idx)
			node = root
			# Selection
			while node.is_expanded and node.children:
				move, move_idx = self._select(state, node)
				path.append((node, move, move_idx))
				state.apply_move(move)
				node = node.children[move_idx]
			# Expansion
			value = self._expand(state, node, policy_fn)
			# Backup
			self._backup(path, value, state.side_to_move)
		return root

	def _select(self, state: GameState, node: Node) -> Tuple[Move, int]:
		N_sum = node.total_visit() + 1
		best_score = -1e9
		best = None
		for move_idx, edge in node.edges.items():
			U = self.cpuct * edge.P * math.sqrt(N_sum) / (1 + edge.N)
			score = edge.Q + U
			if score > best_score:
				best_score = score
				best = move_idx
		assert best is not None
		from_sq = best // C.NUM_SQUARES
		to_sq = best % C.NUM_SQUARES
		pt = C.piece_type(state.board[from_sq])
		move = Move.make(from_sq, to_sq, pt)
		return move, best

	def _expand(self, state: GameState, node: Node, policy_fn: PolicyFn, add_noise: bool = False) -> float:
		if node.is_expanded:
			# return leaf value (side_to_move POV)
			return 0.0
		mask = legal_move_mask(state)
		policy, value = policy_fn(state)
		# mask illegal
		s = 0.0
		priors: Dict[int, float] = {}
		for i in range(C.NUM_SQUARES * C.NUM_SQUARES):
			p = policy[i] * mask[i]
			if p > 0:
				priors[i] = p
				s += p
		if s > 0:
			for k in priors:
				priors[k] /= s
		else:
			# No prior; uniform over legal
			legal_indices = [i for i in range(len(mask)) if mask[i] > 0]
			w = 1.0 / max(1, len(legal_indices))
			priors = {i: w for i in legal_indices}
		# Optional Dirichlet noise at root
		if add_noise and priors:
			legal_indices = list(priors.keys())
			noise = _sample_dirichlet(len(legal_indices), self.dirichlet_alpha)
			for i, idx in enumerate(legal_indices):
				priors[idx] = (1 - self.dirichlet_frac) * priors[idx] + self.dirichlet_frac * noise[i]
		# Create edges/children
		for idx, p in priors.items():
			node.edges[idx] = EdgeStats(P=p)
			node.children[idx] = Node(parent=node, prior=p)
		node.is_expanded = True
		return value

	def _backup(self, path: List[Tuple[Node, Move, int]], value: float, leaf_side_to_move: int) -> None:
		# value is from leaf state's POV; along path we alternate perspective
		sign = 1.0
		for node, _move, idx in reversed(path):
			es = node.edges[idx]
			es.N += 1
			es.W += sign * value
			es.Q = es.W / es.N
			sign = -sign

	def action_probs(self, root: Node, tau: float = 1.0) -> Dict[int, float]:
		"""Return action probabilities over 8100 indices from root visit counts with temperature tau.
		If tau==0, return one-hot at argmax.
		"""
		counts = {idx: es.N for idx, es in root.edges.items()}
		if not counts:
			return {}
		if tau <= 1e-6:
			best = max(counts.items(), key=lambda kv: kv[1])[0]
			return {best: 1.0}
		# N^(1/tau)
		weights = {idx: (n ** (1.0 / tau)) for idx, n in counts.items()}
		s = sum(weights.values())
		return {idx: w / s for idx, w in weights.items()} if s > 0 else {idx: 1.0 / len(weights) for idx in weights}


def _sample_dirichlet(k: int, alpha: float) -> List[float]:
	# Sample using Gamma variates
	if k <= 0:
		return []
	vals = [random.gammavariate(alpha, 1.0) for _ in range(k)]
	s = sum(vals)
	if s <= 0:
		return [1.0 / k] * k
	return [v / s for v in vals]



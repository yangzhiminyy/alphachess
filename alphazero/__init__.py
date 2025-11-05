"""
AlphaZero framework: game-agnostic MCTS, neural network, and training.

Usage:
1. Implement GameInterface for your game
2. Create PolicyValueNet with appropriate NetworkConfig
3. Use GenericMCTS for self-play
4. Use Trainer for model updates
"""

from .game_interface import GameInterface
from .network import PolicyValueNet, NetworkConfig, create_xiangqi_net
from .mcts_generic import GenericMCTS
from .trainer import Trainer, TrainerConfig, AlphaZeroDataset

__all__ = [
	"GameInterface",
	"PolicyValueNet",
	"NetworkConfig",
	"create_xiangqi_net",
	"GenericMCTS",
	"Trainer",
	"TrainerConfig",
	"AlphaZeroDataset",
]


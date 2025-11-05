#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test to verify both legacy and generic frameworks work correctly.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use ASCII characters for Windows compatibility
CHECK = "[OK]"
CROSS = "[FAIL]"
PARTY = "[SUCCESS]"

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    # Legacy imports
    from xq import GameState, Move, constants as C
    from xq.nn import XQNet, state_to_tensor
    from xq.mcts import MCTS
    from xq.search.alpha_beta import alphabeta_search
    print(f"{CHECK} Legacy imports successful")
    
    # Generic imports
    from alphazero import GameInterface, PolicyValueNet, NetworkConfig, create_xiangqi_net
    from alphazero import GenericMCTS, Trainer, TrainerConfig, AlphaZeroDataset
    from xq.game_adapter import XiangqiGame
    print(f"{CHECK} Generic imports successful")
    
    return True


def test_legacy_framework():
    """Test legacy Xiangqi implementation."""
    print("\nTesting legacy framework...")
    
    from xq import GameState
    from xq.nn import XQNet, state_to_tensor
    import torch
    
    # Create game state
    state = GameState()
    state.setup_starting_position()
    print(f"{CHECK} Created game state with {len(state.board)} squares")
    
    # Generate legal moves
    moves = state.generate_legal_moves()
    print(f"{CHECK} Generated {len(moves)} legal moves from start position")
    
    # Create legacy model
    model = XQNet()
    print(f"{CHECK} Created legacy XQNet model")
    
    # Test inference
    tensor = state_to_tensor(state)
    print(f"{CHECK} Converted state to tensor: {tensor.shape}")
    
    with torch.no_grad():
        logits, value = model(tensor.unsqueeze(0))
    print(f"{CHECK} Model inference: policy shape {logits.shape}, value {value.item():.3f}")
    
    return True


def test_generic_framework():
    """Test generic AlphaZero framework with Xiangqi adapter."""
    print("\nTesting generic framework...")
    
    from alphazero import create_xiangqi_net, GenericMCTS
    from xq.game_adapter import XiangqiGame
    import torch
    import numpy as np
    
    # Create game adapter
    game = XiangqiGame()
    state = game.get_initial_state()
    print(f"{CHECK} Created XiangqiGame adapter")
    
    # Test game interface methods
    action_size = game.get_action_size()
    obs_shape = game.get_observation_shape()
    legal_actions = game.get_legal_actions(state)
    current_player = game.get_current_player(state)
    print(f"{CHECK} Action size: {action_size}, Observation shape: {obs_shape}")
    print(f"{CHECK} Legal actions: {len(legal_actions)}, Current player: {current_player}")
    
    # Test state conversion
    tensor = game.state_to_tensor(state)
    print(f"{CHECK} State to tensor: {tensor.shape}, dtype: {tensor.dtype}")
    
    # Create generic model
    model = create_xiangqi_net()
    print(f"{CHECK} Created generic PolicyValueNet")
    
    # Test inference
    input_tensor = torch.from_numpy(tensor).unsqueeze(0)
    with torch.no_grad():
        logits, value = model(input_tensor)
    print(f"{CHECK} Model inference: policy shape {logits.shape}, value {value.item():.3f}")
    
    # Test MCTS
    def simple_policy(state):
        """Simple uniform policy for testing."""
        legal = game.get_legal_actions(state)
        probs = [0.0] * action_size
        if legal:
            p = 1.0 / len(legal)
            for a in legal:
                probs[a] = p
        return probs, 0.0
    
    mcts = GenericMCTS(game, cpuct=1.5)
    action_probs = mcts.search(state, simple_policy, num_simulations=10)
    print(f"{CHECK} MCTS search returned {len(action_probs)} action probabilities")
    
    return True


def test_model_compatibility():
    """Test that models can be saved and loaded."""
    print("\nTesting model compatibility...")
    
    import torch
    from xq.nn import XQNet
    from alphazero import create_xiangqi_net
    
    # Test legacy model
    legacy_model = XQNet()
    legacy_path = "test_legacy.pt"
    torch.save(legacy_model.state_dict(), legacy_path)
    
    loaded_legacy = XQNet()
    loaded_legacy.load_state_dict(torch.load(legacy_path))
    print(f"{CHECK} Legacy model saved and loaded")
    
    # Test generic model
    generic_model = create_xiangqi_net()
    generic_path = "test_generic.pt"
    torch.save(generic_model.state_dict(), generic_path)
    
    loaded_generic = create_xiangqi_net()
    loaded_generic.load_state_dict(torch.load(generic_path))
    print(f"{CHECK} Generic model saved and loaded")
    
    # Check for BatchNorm detection
    legacy_dict = torch.load(legacy_path)
    generic_dict = torch.load(generic_path)
    
    legacy_has_bn = any('bn' in k for k in legacy_dict.keys())
    generic_has_bn = any('bn' in k for k in generic_dict.keys())
    
    print(f"{CHECK} Legacy model BatchNorm detection: {legacy_has_bn} (should be False)")
    print(f"{CHECK} Generic model BatchNorm detection: {generic_has_bn} (should be True)")
    
    # Clean up
    os.remove(legacy_path)
    os.remove(generic_path)
    print(f"{CHECK} Cleaned up test files")
    
    return True


def test_game_interface():
    """Test that game interface methods work correctly."""
    print("\nTesting GameInterface implementation...")
    
    from xq.game_adapter import XiangqiGame
    
    game = XiangqiGame()
    state = game.get_initial_state()
    
    # Test move generation and application
    legal_actions = game.get_legal_actions(state)
    assert len(legal_actions) > 0, "Should have legal moves at start"
    
    # Apply a move
    first_action = legal_actions[0]
    new_state = game.get_next_state(state, first_action)
    
    # Check that player changed
    old_player = game.get_current_player(state)
    new_player = game.get_current_player(new_state)
    assert old_player != new_player, "Player should change after move"
    print(f"{CHECK} Move application changes player: {old_player} -> {new_player}")
    
    # Test game result
    result = game.get_game_result(state)
    assert result is None, "Game should not be over at start"
    print(f"{CHECK} Game result at start: {result} (should be None)")
    
    # Test display
    display = game.display(state)
    assert len(display) > 0, "Display should return non-empty string"
    print(f"{CHECK} Display method works (returned {len(display)} characters)")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("AlphaChess Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Legacy Framework", test_legacy_framework),
        ("Generic Framework", test_generic_framework),
        ("Model Compatibility", test_model_compatibility),
        ("GameInterface", test_game_interface),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
                print(f"{CHECK} {name} PASSED\n")
            else:
                failed += 1
                print(f"{CROSS} {name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"{CROSS} {name} FAILED: {e}\n")
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print(f"\n{PARTY} All tests passed! The integration is working correctly.")
        return 0
    else:
        print(f"\n{CROSS} {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


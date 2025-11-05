# Changelog

All notable changes to the AlphaChess project.

## [Unreleased]

## [2.0.0] - Generic Framework Release

### Added - Generic AlphaZero Framework

#### Core Components (`alphazero/`)
- **`game_interface.py`**: Abstract base class `GameInterface` defining the contract for any board game
  - Methods: `get_initial_state`, `get_action_size`, `get_observation_shape`, `get_legal_actions`, `get_next_state`, `get_game_result`, `get_current_player`, `state_to_tensor`, `get_canonical_form`, `get_symmetries`, `display`
  
- **`network.py`**: Generic `PolicyValueNet` with configurable architecture
  - `NetworkConfig` dataclass for easy configuration
  - Residual blocks with BatchNorm
  - Separate policy and value heads
  - Factory function `create_xiangqi_net()` for Xiangqi-specific setup
  
- **`mcts_generic.py`**: Game-agnostic MCTS implementation
  - Works with any `GameInterface` implementation
  - PUCT algorithm with Dirichlet noise
  - Configurable exploration parameters
  
- **`trainer.py`**: Generic training pipeline
  - `Trainer` class with configurable loss weights
  - `AlphaZeroDataset` for loading self-play data
  - Support for checkpointing and resuming

#### Xiangqi Adapter
- **`xq/game_adapter.py`**: `XiangqiGame` class implementing `GameInterface`
  - Bridges generic framework with Xiangqi-specific `GameState`
  - Converts between internal representation and generic action indices

#### New Scripts
- **`scripts/train_generic.py`**: Training script using generic framework
  - Supports any game implementing `GameInterface`
  - Detailed training metrics (separate policy and value loss)
  - Compatible with generic `PolicyValueNet` models
  
- **`scripts/self_play_generic.py`**: Self-play data generation using generic framework
  - Game-agnostic implementation
  - Uses `GenericMCTS` for move selection
  - Outputs standardized JSONL format

- **`scripts/test_integration.py`**: Comprehensive integration test suite
  - Tests both legacy and generic frameworks
  - Validates model compatibility
  - Checks `GameInterface` implementation
  - Reports: 5 test groups, all passing

#### Documentation
- **`README_FRAMEWORK.md`**: Complete architecture documentation
  - Framework overview and design philosophy
  - Usage guide for both frameworks
  - Instructions for adding new games
  - Performance notes and best practices
  
- **`MIGRATION_GUIDE.md`**: Step-by-step migration guide
  - Code examples comparing legacy vs. generic
  - Troubleshooting common issues
  - Recommended migration path
  - Future roadmap

### Changed - Backward Compatibility Updates

#### API Server (`api/server.py`)
- **`_load_model()`**: New function to auto-detect model type
  - Inspects state dict for BatchNorm keys
  - Loads `XQNet` (legacy) or `PolicyValueNet` (generic) automatically
  - Returns model and framework type
  
- **`/api/model/framework`**: New endpoint to query loaded model info
  - Returns: `loaded`, `path`, `framework` (legacy/generic)
  
- Updated MCTS endpoints to use `_load_model()` for seamless compatibility

#### Legacy Code
- **`xq/nn.py`**: Added import of generic components with fallback
  - Added deprecation note in docstring
  - Recommends using `create_xiangqi_net()` for new code
  - Full backward compatibility maintained

- **`scripts/train.py`**: Added header noting legacy status
  - Still fully functional
  - Points to `train_generic.py` for new projects

### Technical Details

#### Model Differentiation
Legacy models (no BatchNorm):
```
stem -> ResidualBlock (Conv only) -> Policy/Value heads
```

Generic models (with BatchNorm):
```
stem + BN -> ResidualBlock (Conv + BN) -> BN + Policy/Value heads
```

Detection algorithm:
```python
has_bn = any('bn' in key for key in state_dict.keys())
```

#### Performance Impact
- Training: Generic models may be 5-10% slower due to BatchNorm, but converge better
- Inference: No significant difference in eval mode
- Memory: Generic models use ~5-10% more memory for BN statistics

### Testing

All integration tests passing:
```
✓ Import Test (legacy + generic imports)
✓ Legacy Framework (XQNet, state, moves, inference)
✓ Generic Framework (GameInterface, PolicyValueNet, GenericMCTS)
✓ Model Compatibility (save/load both types)
✓ GameInterface (move generation, player switching)
```

## [1.0.0] - Initial Release

### Features

#### Core Xiangqi Engine (`xq/`)
- **`constants.py`**: Board dimensions, piece types, indexing
- **`move.py`**: 32-bit move encoding
- **`zobrist.py`**: Zobrist hashing for position caching
- **`state.py`**: Complete Xiangqi game logic
  - Move generation (pseudo-legal and legal)
  - Check detection
  - Threefold repetition
  - Long check/chase detection (Chinese rules)
  - Game adjudication
  
- **`policy.py`**: Move to action index mapping (8100-dimensional)
- **`nn.py`**: Simple residual CNN (`XQNet`)
  - 15 input planes (14 pieces + side-to-move)
  - 3 residual blocks
  - Policy head (8100 outputs)
  - Value head (scalar in [-1, 1])

#### Search Algorithms
- **`search/alpha_beta.py`**: Alpha-Beta pruning
  - Negamax with transposition table
  - Quiescence search
  - Move ordering (MVV/LVA, history, killer heuristics)
  
- **`mcts.py`**: Monte Carlo Tree Search
  - PUCT algorithm
  - Dirichlet noise for exploration
  - Temperature-controlled action selection
  - Time-based search limits

#### Self-Play and Training
- **`selfplay.py`**: Self-play data generation
  - Supports MCTS and MCTS+NN modes
  - Outputs JSONL format
  - Configurable temperature schedule
  
- **`train_loop.py`**: Asynchronous training loop
  - Orchestrates self-play, data saving, and training
  - Status tracking and stop control

#### API Server (`api/server.py`)
- FastAPI-based REST API
- Endpoints:
  - Game management (create, get, move, undo)
  - Legal moves generation
  - Best move (Alpha-Beta and MCTS)
  - Policy mask visualization
  - Human-AI play
  - Model inspection
  - Training loop control
- CORS support for browser access
- Static file serving for frontend

#### Web Frontend (`web/`)
- **`index.html`** + **`app.js`**: Main game interface
  - Interactive Chinese Chess board
  - Piece visualization (楚河 汉界)
  - Move history with descriptions
  - Board flipping (red/black perspective)
  - AI thinking indicator
  - Configurable AI strength
  
- **`model.html`** + **`model.js`**: Model viewer
  - List available models
  - View model structure (paginated)
  - Display parameters and gradients
  - Network topology visualization

#### Training Scripts
- **`scripts/train.py`**: Train XQNet from JSONL
- **`scripts/self_play.py`**: Generate self-play games
- **`scripts/demo_client.py`**: CLI API client

### Game Rules Implementation
- ✅ All piece movements (Pawn, Cannon, Knight, Bishop, Advisor, Rook, King)
- ✅ Palace and river constraints
- ✅ General facing rule
- ✅ Check and checkmate detection
- ✅ Stalemate detection
- ✅ Threefold repetition
- ✅ Perpetual check detection
- ✅ Long chase/attack adjudication (Chinese rules)

### Architecture Highlights
- **Board Representation**: 9×10 integer matrix (signed for color)
- **Move Encoding**: 32-bit integer (from_sq, to_sq, piece types, flags)
- **Zobrist Hashing**: Incremental updates for fast position caching
- **Legal Move Masking**: 8100-bit vector for neural network
- **Multi-channel Input**: 15 planes for neural network input

---

## Version Numbering

- **1.x.x**: Legacy Xiangqi-specific implementation
- **2.x.x**: Generic AlphaZero framework with backward compatibility
- **3.x.x** (planned): Multi-game support with unified training

## Migration Timeline

- **v1.0.0**: Initial release with Xiangqi engine
- **v2.0.0**: Generic framework added, legacy still works
- **v3.0.0** (future): Full multi-game training pipeline

## Compatibility Matrix

| Version | Legacy Scripts | Generic Scripts | API Server | Frontend |
|---------|---------------|----------------|------------|----------|
| 1.x.x   | ✅            | ❌             | ✅         | ✅       |
| 2.x.x   | ✅            | ✅             | ✅         | ✅       |
| 3.x.x   | ✅            | ✅             | ✅         | ✅       |

## Breaking Changes

**None**. Version 2.0.0 maintains full backward compatibility with 1.x.x code.

## Deprecation Notices

The following components are deprecated but still supported:
- `xq.nn.XQNet` → Use `alphazero.create_xiangqi_net()`
- `xq.mcts.MCTS` → Use `alphazero.GenericMCTS`
- `xq.selfplay` → Use `scripts/self_play_generic.py`
- `scripts/train.py` → Use `scripts/train_generic.py`

These will remain functional indefinitely but won't receive new features.


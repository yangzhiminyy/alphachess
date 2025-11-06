# Migration Guide: Legacy to Generic Framework

## Overview

This guide helps you migrate from the legacy Xiangqi-specific implementation to the new generic AlphaZero framework. The generic framework offers better extensibility, cleaner architecture, and the ability to easily add new games.

## What's New in the Generic Framework?

### 1. **Game-Agnostic Architecture**
- **GameInterface**: Abstract base class for any board game
- **PolicyValueNet**: Generic neural network with BatchNorm
- **GenericMCTS**: Reusable MCTS implementation
- **Trainer**: Modular training pipeline

### 2. **Improved Neural Network**
- Added **BatchNorm** layers for better convergence
- Configurable architecture via `NetworkConfig`
- Factory functions for quick setup

### 3. **Better Code Organization**
- Clear separation between game logic and AI algorithms
- Easier to test and maintain
- Ready for multi-game support

## Backward Compatibility

**Important**: All legacy code continues to work! The API server automatically detects and loads both legacy and generic models.

## Quick Start with Generic Framework

### Step 1: Generate Self-Play Data

```bash
# Using generic self-play (NEW)
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 50 \
    --sims 200 \
    --out data/selfplay_generic.jsonl

# Or using legacy self-play (still works)
python scripts/self_play.py \
    --games 50 \
    --engine mcts \
    --sims 200 \
    --out data/selfplay_legacy.jsonl
```

### Step 2: Train a Model

```bash
# Using generic trainer (NEW)
python scripts/train_generic.py \
    --game xiangqi \
    --data data/selfplay_generic.jsonl \
    --model_out models/generic_v1.pt \
    --epochs 10 \
    --batch_size 64

# Or using legacy trainer (still works)
python scripts/train.py \
    --data data/selfplay_legacy.jsonl \
    --model_out models/legacy_v1.pt \
    --epochs 10
```

### Step 3: Use the Model

Both model types work with the API server:

```bash
# Start the server
uvicorn api.server:app --host 127.0.0.1 --port 8000

# Check which framework is loaded
curl http://127.0.0.1:8000/api/model/framework
```

The frontend at `http://127.0.0.1:8000/web/` works with both model types automatically.

## Code Examples

### Legacy Approach (Still Supported)

```python
from xq import GameState
from xq.nn import XQNet, state_to_tensor, infer_policy_value
from xq.mcts import MCTS
import torch

# Create model
model = XQNet()
model.load_state_dict(torch.load('models/legacy.pt'))

# Create game
state = GameState()
state.setup_starting_position()

# Get moves
moves = state.generate_legal_moves()

# Run MCTS
def policy_fn(state):
    tensor = state_to_tensor(state).unsqueeze(0)
    with torch.no_grad():
        logits, value = model(tensor)
    policy = torch.softmax(logits[0], dim=-1).tolist()
    return policy, float(value.item())

mcts = MCTS()
root = mcts.run(state, policy_fn, num_simulations=400)
probs = mcts.action_probs(root, tau=1.0)
```

### Generic Approach (Recommended)

```python
from alphazero import create_xiangqi_net, GenericMCTS
from xq.game_adapter import XiangqiGame
import torch

# Create game adapter
game = XiangqiGame()

# Create model
model = create_xiangqi_net()
model.load_state_dict(torch.load('models/generic.pt'))

# Get initial state
state = game.get_initial_state()

# Get legal actions
legal_actions = game.get_legal_actions(state)

# Define policy function
def policy_fn(state):
    tensor = torch.from_numpy(game.state_to_tensor(state)).unsqueeze(0)
    with torch.no_grad():
        logits, value = model(tensor)
    policy = torch.softmax(logits[0], dim=-1).tolist()
    return policy, float(value.item())

# Run MCTS
mcts = GenericMCTS(game, cpuct=1.5)
action_probs = mcts.search(state, policy_fn, num_simulations=400)

# Apply best action
best_action = max(action_probs.items(), key=lambda x: x[1])[0]
next_state = game.get_next_state(state, best_action)
```

## Key Differences

| Feature | Legacy | Generic |
|---------|--------|---------|
| **Package** | `xq.*` | `alphazero.*` + game adapters |
| **State Type** | `GameState` (Xiangqi-specific) | `Any` (via `GameInterface`) |
| **Move Representation** | `Move` dataclass | Action index (`int`) |
| **Network** | `XQNet` (no BatchNorm) | `PolicyValueNet` (with BatchNorm) |
| **MCTS** | `xq.mcts.MCTS` | `alphazero.GenericMCTS` |
| **Training** | `scripts/train.py` | `scripts/train_generic.py` |
| **Extensibility** | Xiangqi only | Any game via adapter |

## API Compatibility

### Model Detection

The API server automatically detects model type:

```python
# In api/server.py
def _load_model(model_path: str):
    state_dict = torch.load(model_path)
    has_bn = any('bn' in key for key in state_dict.keys())
    
    if has_bn:
        # Generic model with BatchNorm
        model = create_xiangqi_net()
    else:
        # Legacy model without BatchNorm
        model = XQNet()
    
    model.load_state_dict(state_dict)
    return model, "generic" if has_bn else "legacy"
```

### Check Current Framework

```bash
curl http://127.0.0.1:8000/api/model/framework
```

Response:
```json
{
  "loaded": true,
  "path": "models/generic_v1.pt",
  "framework": "generic"
}
```

## Adding New Games

With the generic framework, adding new games is straightforward:

### 1. Implement GameInterface

```python
# games/chess/game_adapter.py
from alphazero import GameInterface

class ChessGame(GameInterface):
    def get_initial_state(self):
        # Return starting chess position
        pass
    
    def get_action_size(self):
        return 4672  # From-to + promotions
    
    def get_observation_shape(self):
        return (12, 8, 8)  # 6 piece types × 2 colors
    
    # ... implement all abstract methods
```

### 2. Create Network Config

```python
# games/chess/network.py
from alphazero import NetworkConfig, PolicyValueNet

def create_chess_net():
    config = NetworkConfig(
        input_channels=12,
        board_height=8,
        board_width=8,
        action_size=4672,
        hidden_channels=128,
        num_res_blocks=10
    )
    return PolicyValueNet(config)
```

### 3. Update Scripts

```python
# scripts/train_generic.py
if args.game == "xiangqi":
    game = XiangqiGame()
    model = create_xiangqi_net()
elif args.game == "chess":
    game = ChessGame()
    model = create_chess_net()
```

## Performance Considerations

### Training Speed

- **Generic models** (with BatchNorm) may train slightly slower but often converge better
- **Legacy models** are simpler and faster for quick experiments

### Inference Speed

Both frameworks have similar inference speeds. The generic framework's BatchNorm overhead is negligible during evaluation mode.

### Memory Usage

Generic models use slightly more memory due to BatchNorm statistics, but the difference is minimal (~5-10%).

## Testing Your Migration

Run the integration test suite:

```bash
python scripts/test_integration.py
```

Expected output:
```
============================================================
AlphaChess Integration Test Suite
============================================================
[OK] Import Test PASSED
[OK] Legacy Framework PASSED
[OK] Generic Framework PASSED
[OK] Model Compatibility PASSED
[OK] GameInterface PASSED
============================================================
Results: 5 passed, 0 failed
============================================================
[SUCCESS] All tests passed! The integration is working correctly.
```

## Troubleshooting

### Issue: Model won't load

**Solution**: Check model type detection:
```python
import torch
state_dict = torch.load('your_model.pt')
has_bn = any('bn' in k for k in state_dict.keys())
print(f"Model type: {'generic' if has_bn else 'legacy'}")
```

### Issue: API returns wrong predictions

**Solution**: Ensure you're using the correct model path:
```bash
# Check current model
curl http://127.0.0.1:8000/api/model/framework

# Specify model explicitly
curl -X POST http://127.0.0.1:8000/api/games/YOUR_GAME_ID/best \
  -H "Content-Type: application/json" \
  -d '{"engine": "mcts_nn", "model_path": "models/generic_v1.pt"}'
```

### Issue: Training fails with generic framework

**Solution**: Verify data format:
```python
import json

with open('selfplay.jsonl') as f:
    for line in f:
        game = json.loads(line)
        for record in game['records']:
            assert 'planes' in record
            assert 'pi' in record
            assert 'z' in record
            break
        break
```

## Recommended Migration Path

1. **Phase 1: Test Generic Framework** (Week 1)
   - Run integration tests
   - Generate small self-play dataset with generic scripts
   - Train a test model
   - Compare with legacy model performance

2. **Phase 2: Parallel Operation** (Week 2-3)
   - Run both frameworks side by side
   - Generate training data with both systems
   - Track model performance metrics

3. **Phase 3: Full Migration** (Week 4+)
   - Switch to generic framework as primary
   - Keep legacy code for compatibility
   - Start adding new games

## Future Roadmap

With the generic framework in place, planned features include:

- **Multi-game training**: Train one model on multiple games
- **Transfer learning**: Pre-train on simple games, fine-tune on complex ones
- **Distributed training**: Multi-GPU and multi-node support
- **Model zoo**: Pre-trained models for common board games
- **Web-based training monitor**: Real-time training visualization

## Getting Help

- **Documentation**: See `README_FRAMEWORK.md` for detailed architecture
- **Examples**: Check `scripts/test_integration.py` for working code
- **Issues**: Review error messages in `scripts/train_generic.py` output

## Summary

The generic framework offers:
- ✅ Better code organization
- ✅ Easy extensibility to new games
- ✅ Modern architecture with BatchNorm
- ✅ Full backward compatibility
- ✅ Automatic model type detection

Legacy code still works, so you can migrate at your own pace!


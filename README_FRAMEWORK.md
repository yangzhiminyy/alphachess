# AlphaZero Framework Architecture

## Overview

This project implements an AlphaZero-style engine for Chinese Chess (Xiangqi) with a **modular, game-agnostic architecture**. The codebase is structured to support both:

1. **Legacy Xiangqi-specific implementation** (backward compatible)
2. **Generic AlphaZero framework** (extensible to other games)

## Architecture

### Core Components

```
alphachess/
├── alphazero/                 # Generic AlphaZero framework
│   ├── __init__.py
│   ├── game_interface.py      # Abstract base class for any game
│   ├── network.py             # Generic PolicyValueNet with BatchNorm
│   ├── mcts_generic.py        # Game-agnostic MCTS implementation
│   └── trainer.py             # Generic training pipeline
├── xq/                        # Xiangqi-specific implementation
│   ├── __init__.py
│   ├── constants.py           # Board dimensions, piece types
│   ├── move.py                # 32-bit move encoding
│   ├── zobrist.py             # Zobrist hashing
│   ├── state.py               # Game state, move generation, rules
│   ├── policy.py              # Move indexing for neural network
│   ├── nn.py                  # Legacy XQNet (deprecated)
│   ├── game_adapter.py        # XiangqiGame implementing GameInterface
│   ├── mcts.py                # Legacy MCTS (deprecated)
│   ├── selfplay.py            # Legacy self-play (deprecated)
│   └── search/
│       └── alpha_beta.py      # Alpha-Beta search with pruning
├── api/
│   └── server.py              # FastAPI server (supports both frameworks)
├── scripts/
│   ├── train.py               # Legacy training script
│   ├── train_generic.py       # Generic training script (NEW)
│   ├── self_play.py           # Legacy self-play
│   └── self_play_generic.py   # Generic self-play (NEW)
└── web/                       # React frontend
    ├── index.html             # Main game UI
    ├── app.js                 # Game logic
    ├── model.html             # Model viewer
    └── model.js               # Model inspection
```

## Generic Framework Design

### 1. GameInterface (alphazero/game_interface.py)

The abstract interface that any board game must implement:

```python
class GameInterface(ABC):
    @abstractmethod
    def get_initial_state(self) -> Any: ...
    
    @abstractmethod
    def get_action_size(self) -> int: ...
    
    @abstractmethod
    def get_observation_shape(self) -> Tuple[int, ...]: ...
    
    @abstractmethod
    def get_legal_actions(self, state: Any) -> List[int]: ...
    
    @abstractmethod
    def get_next_state(self, state: Any, action: int) -> Any: ...
    
    @abstractmethod
    def get_game_result(self, state: Any) -> Optional[float]: ...
    
    @abstractmethod
    def get_current_player(self, state: Any) -> int: ...
    
    @abstractmethod
    def state_to_tensor(self, state: Any) -> Any: ...
    
    @abstractmethod
    def get_canonical_form(self, state: Any, player: int) -> Any: ...
    
    @abstractmethod
    def get_symmetries(self, state: Any, pi: List[float]) -> List[Tuple[Any, List[float]]]: ...
    
    @abstractmethod
    def display(self, state: Any) -> str: ...
```

### 2. PolicyValueNet (alphazero/network.py)

A generic residual CNN that can be configured for any board game:

```python
@dataclass
class NetworkConfig:
    input_channels: int      # e.g., 15 for Xiangqi
    board_height: int        # e.g., 10 for Xiangqi
    board_width: int         # e.g., 9 for Xiangqi
    action_size: int         # e.g., 8100 for Xiangqi
    hidden_channels: int = 64
    num_res_blocks: int = 3

class PolicyValueNet(nn.Module):
    # Generic architecture with BatchNorm
    # - Policy head: outputs action_size logits
    # - Value head: outputs scalar in [-1, 1]
```

**Factory function for Xiangqi:**
```python
from alphazero.network import create_xiangqi_net
model = create_xiangqi_net()  # Pre-configured for Xiangqi
```

### 3. GenericMCTS (alphazero/mcts_generic.py)

Game-agnostic MCTS that operates on any `GameInterface`:

```python
mcts = GenericMCTS(game_interface, policy_fn, num_simulations=800)
action_probs = mcts.search(state, temperature=1.0)
```

### 4. Trainer (alphazero/trainer.py)

Generic training pipeline with configurable loss weights:

```python
config = TrainerConfig(
    learning_rate=1e-3,
    weight_decay=1e-4,
    policy_loss_weight=1.0,
    value_loss_weight=1.0
)
trainer = Trainer(model, config, device='cuda')
trainer.train_step(states, policies, values)
trainer.save('checkpoint.pt')
```

## Xiangqi Adapter (xq/game_adapter.py)

The `XiangqiGame` class bridges the generic framework with Xiangqi-specific logic:

```python
from alphazero import GameInterface
from xq.game_adapter import XiangqiGame

game = XiangqiGame()
state = game.get_initial_state()
legal_actions = game.get_legal_actions(state)
next_state = game.get_next_state(state, action)
```

## Usage Guide

### Training Pipeline

#### Using the Generic Framework (Recommended for New Projects)

**Step 1: Generate Self-Play Data**
```bash
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 100 \
    --sims 400 \
    --max_moves 200 \
    --model models/generic_latest.pt \  # Optional: use trained model
    --out data/selfplay_001.jsonl
```

**Step 2: Train the Model**
```bash
python scripts/train_generic.py \
    --game xiangqi \
    --data data/selfplay_001.jsonl \
    --model_out models/generic_latest.pt \
    --epochs 10 \
    --batch_size 64 \
    --lr 0.001
```

**Step 3: Iterate**
Repeat steps 1-2, using the trained model for self-play to generate better data.

#### Using the Legacy Framework (Backward Compatible)

```bash
# Self-play
python scripts/self_play.py \
    --games 50 \
    --engine mcts \
    --sims 200 \
    --out selfplay.jsonl

# Train
python scripts/train.py \
    --data selfplay.jsonl \
    --model_out models/latest.pt \
    --epochs 10
```

### API Server

The FastAPI server automatically detects and loads both legacy and generic models:

```bash
# Start server
uvicorn api.server:app --host 127.0.0.1 --port 8000

# Check which framework is loaded
curl http://127.0.0.1:8000/api/model/framework
```

**Response:**
```json
{
  "loaded": true,
  "path": "models/generic_latest.pt",
  "framework": "generic"  // or "legacy"
}
```

### Frontend

Access the web interface at:
- **Main Game**: http://127.0.0.1:8000/web/
- **Model Viewer**: http://127.0.0.1:8000/web/model.html

The frontend works with both legacy and generic models transparently.

## Model Detection

The API server automatically detects model type by inspecting state dict keys:

- **Generic models**: Contain BatchNorm layers (keys with `bn`)
- **Legacy models**: No BatchNorm (simple Conv + ReLU)

```python
# In api/server.py
def _load_model(model_path: str):
    state_dict = torch.load(model_path)
    has_bn = any('bn' in key for key in state_dict.keys())
    
    if has_bn:
        model = create_xiangqi_net()  # Generic
    else:
        model = XQNet()  # Legacy
    
    model.load_state_dict(state_dict)
    return model
```

## Adding New Games

To add a new game (e.g., Go, Chess, Shogi):

1. **Implement GameInterface**
   ```python
   # games/go/game_adapter.py
   from alphazero import GameInterface
   
   class GoGame(GameInterface):
       def get_initial_state(self): ...
       def get_action_size(self): return 19*19 + 1  # pass move
       # ... implement all abstract methods
   ```

2. **Create Network Configuration**
   ```python
   # games/go/network.py
   from alphazero import NetworkConfig, PolicyValueNet
   
   def create_go_net():
       config = NetworkConfig(
           input_channels=17,  # 8 history + side
           board_height=19,
           board_width=19,
           action_size=362,    # 19*19 + 1
           hidden_channels=128,
           num_res_blocks=10
       )
       return PolicyValueNet(config)
   ```

3. **Use Generic Scripts**
   ```bash
   python scripts/train_generic.py --game go --data go_selfplay.jsonl
   python scripts/self_play_generic.py --game go --games 100
   ```

## Migration Guide

### From Legacy to Generic

**Legacy Code:**
```python
from xq.nn import XQNet, state_to_tensor, infer_policy_value
from xq.mcts import MCTS

model = XQNet()
model.load_state_dict(torch.load('legacy.pt'))
```

**Generic Code:**
```python
from alphazero import create_xiangqi_net, GenericMCTS
from xq.game_adapter import XiangqiGame

game = XiangqiGame()
model = create_xiangqi_net()
model.load_state_dict(torch.load('generic.pt'))
mcts = GenericMCTS(game, policy_fn, num_simulations=800)
```

### Converting Existing Models

Legacy models can continue to work as-is. To retrain with the generic framework:

1. Generate new self-play data using `self_play_generic.py`
2. Train a new model using `train_generic.py`
3. The API will automatically detect and use the new model type

## Key Differences

| Feature | Legacy | Generic |
|---------|--------|---------|
| **Architecture** | Simple Conv + ReLU | Conv + BatchNorm + ReLU |
| **Game Support** | Xiangqi only | Any game via GameInterface |
| **Code Location** | `xq/` package | `alphazero/` + game adapters |
| **Extensibility** | Hardcoded | Abstract interface |
| **Training** | `train.py` | `train_generic.py` |
| **Model Format** | No BatchNorm keys | BatchNorm keys present |

## Performance Notes

- **Generic models** include BatchNorm, which may improve convergence
- **Legacy models** are simpler but Xiangqi-specific
- Both frameworks support GPU acceleration
- API server lazy-loads models to minimize startup time

## Future Extensions

Planned additions to the generic framework:

1. **Multi-game training**: Train a single model on multiple games
2. **Transfer learning**: Pre-train on simple games, fine-tune on complex ones
3. **Distributed self-play**: Parallel game generation across multiple workers
4. **ELO rating system**: Track model improvement over iterations
5. **Opening book integration**: Reduce early-game exploration cost

## References

- **AlphaZero Paper**: Silver et al., "Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm" (2017)
- **AlphaGo Zero**: Silver et al., "Mastering the game of Go without human knowledge" (2017)
- **Chinese Chess Rules**: http://www.xqinenglish.com/

## License

This project is provided as-is for educational and research purposes.


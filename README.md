![chess board](/screenshots/board.png)

# AlphaChess - Chinese Chess AI with AlphaZero

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English Documentation

### Project Overview

**AlphaChess** is a complete implementation of an AlphaZero-style reinforcement learning system for Chinese Chess (Xiangqi). This project demonstrates advanced AI techniques including Monte Carlo Tree Search (MCTS), deep neural networks, and self-play training, all wrapped in a modern web application with REST API.

**Key Features:**
- 🎮 Full Xiangqi game engine with strict rule enforcement
- 🧠 AlphaZero-style neural network (Policy-Value Network)
- 🌲 Monte Carlo Tree Search (MCTS) with PUCT algorithm
- 🔍 Alpha-Beta search with advanced optimizations
- 🎯 Self-play training pipeline with JSONL data format
- 🏆 Arena/ELO evaluation system for model comparison
- 🌐 Modern web interface with React
- 🔌 RESTful API with FastAPI
- 🎨 Model visualization and inspection tools
- 🔄 Generic framework extensible to other board games
- ☁️ Azure cloud deployment with automated scripts

### Technology Stack

**Backend:**
- Python 3.10+
- PyTorch (Deep Learning)
- FastAPI (REST API)
- NumPy (Numerical Computing)

**Frontend:**
- React 18
- Babel (JSX Compilation)
- Modern CSS3

**Architecture:**
- Model-View-Controller (MVC)
- Abstract interfaces for game-agnostic design
- Modular architecture for easy extension

### Project Structure

```
alphachess/
├── xq/                          # Xiangqi game engine
│   ├── constants.py            # Board dimensions, piece types
│   ├── move.py                 # 32-bit move encoding
│   ├── zobrist.py              # Zobrist hashing for positions
│   ├── state.py                # Core game logic (800+ lines)
│   ├── policy.py               # Move indexing for neural network
│   ├── nn.py                   # Legacy neural network
│   ├── mcts.py                 # MCTS implementation
│   ├── selfplay.py             # Self-play data generation
│   ├── game_adapter.py         # GameInterface adapter
│   └── search/
│       └── alpha_beta.py       # Alpha-Beta with TT, QS
│
├── alphazero/                   # Generic AlphaZero framework
│   ├── game_interface.py       # Abstract game interface
│   ├── network.py              # Generic PolicyValueNet
│   ├── mcts_generic.py         # Game-agnostic MCTS
│   └── trainer.py              # Generic training pipeline
│
├── api/
│   └── server.py               # FastAPI REST API (770+ lines)
│
├── web/                         # React frontend
│   ├── index.html              # Main game interface
│   ├── app.js                  # Game UI logic
│   ├── arena.html              # Arena evaluation
│   ├── arena.js                # Arena UI logic
│   ├── model.html              # Model viewer
│   └── model.js                # Model inspection
│
├── scripts/                     # CLI tools
│   ├── train.py                # Legacy training
│   ├── train_generic.py        # Generic training
│   ├── self_play.py            # Legacy self-play
│   ├── self_play_generic.py    # Generic self-play
│   ├── arena.py                # ELO evaluation
│   └── test_integration.py     # Integration tests
│
└── docs/                        # Documentation
    ├── README_FRAMEWORK.md     # Architecture details
    ├── MIGRATION_GUIDE.md      # Migration guide
    ├── VERSION_COMPARISON.md   # Version comparison
    ├── ARENA_GUIDE.md          # Arena usage guide
    └── CHANGELOG.md            # Version history
```

### Core Components

#### 1. Game Engine (`xq/state.py`)

The heart of the system, implementing complete Xiangqi rules:

**Key Features:**
- 9×10 board representation with signed integers
- Incremental move application with undo support
- Zobrist hashing for fast position lookup
- Pseudo-legal and legal move generation
- Check detection and checkmate adjudication
- Threefold repetition detection
- Chinese-specific rules:
  - Palace constraints for King and Advisors
  - River crossing for Pawns
  - Cannon jump mechanics
  - Knight blocking detection
  - General facing rule
  - Perpetual check/chase detection

**Performance:**
- ~44 legal moves from starting position
- Sub-millisecond move generation
- Zobrist hash for O(1) position lookup

#### 2. Neural Network Architecture

**Input Representation:**
- 15 channels × 10 rows × 9 columns
- Channels: 14 piece types (7 pieces × 2 colors) + 1 side-to-move

**Network Architecture (Generic):**
```
Input (15, 10, 9)
    ↓
Conv2d(3×3) + BatchNorm + ReLU
    ↓
N × Residual Blocks
    ↓
┌──────────────┬──────────────┐
│ Policy Head  │  Value Head  │
│              │              │
│ Conv(1×1)    │  Conv(1×1)   │
│ + BatchNorm  │  + BatchNorm │
│ + Flatten    │  + Flatten   │
│ + Linear     │  + Linear    │
│              │  + Tanh      │
│ (8100 dims)  │  (scalar)    │
└──────────────┴──────────────┘
```

**Key Parameters:**
- `hidden_channels`: 64 (default), 128 (advanced)
- `num_res_blocks`: 3 (default), 7-10 (advanced)
- Action space: 8100 (90×90 from-to moves)
- Value range: [-1, 1] (loss to win)

**Network Types:**
1. **Legacy XQNet**: Simple CNN without BatchNorm
2. **Generic PolicyValueNet**: Modern architecture with BatchNorm

#### 3. Search Algorithms

##### Monte Carlo Tree Search (MCTS)

**Algorithm:** PUCT (Predictor + Upper Confidence Bound for Trees)

**Formula:**
$$ UCT = Q(s,a) + c\_puct × P(s,a) × \frac{\sqrt{N(s)} }{(1 + N(s,a))} $$

**Features:**
- Dirichlet noise for exploration (α=0.3)
- Temperature parameter for action selection
- Virtual loss for parallel search
- Legal move masking

**Parameters:**
- `num_simulations`: 100-800 (default: 200)
- `c_puct`: 1.5 (exploration constant)
- `temperature`: 1.0 (exploration) → 0.1 (exploitation)

##### Alpha-Beta Search

**Features:**
- Negamax framework
- Transposition Table (TT) with Zobrist hashing
- Quiescence search for tactical stability
- Move ordering:
  - MVV/LVA (Most Valuable Victim / Least Valuable Attacker)
  - History heuristic
  - Killer moves

**Parameters:**
- `depth`: 3-6 (default: 3)
- `tt_size_mb`: 256 (transposition table size)

#### 4. Training Pipeline

**Self-Play Process:**
```
1. Initialize game from starting position
2. For each move:
   - Run MCTS (with Dirichlet noise)
   - Sample action based on visit counts
   - Apply move to board
3. Record (state, policy, value) tuples
4. Continue until game ends
5. Assign final outcome to all positions
6. Save to JSONL format
```

**Training Process:**
```
1. Load self-play data from JSONL
2. Create PyTorch DataLoader
3. For each epoch:
   - Forward pass: predict policy and value
   - Loss = CrossEntropy(policy) + MSE(value)
   - Backward pass and optimize
4. Save checkpoint
```

**Data Format (JSONL):**
```json
{
  "game_id": 0,
  "result": 1,
  "records": [
    {
      "planes": [[...], ...],  // 15×90 board state
      "pi": {"123": 0.15, ...}, // Policy distribution
      "z": 1.0                  // Game outcome
    }
  ],
  "timestamp": "2025-11-05T..."
}
```

### REST API Reference

Base URL: `http://127.0.0.1:8000/api`

#### Game Management

**Create Game**
```
POST /games
Body: {
  "squares": [int] (optional),
  "side_to_move": int (optional)
}
Response: {
  "game_id": "uuid",
  "state": {...}
}
```

**Get Game State**
```
GET /games/{game_id}
Response: {
  "board": [int],
  "side_to_move": int,
  "legal_moves": [...]
}
```

**Make Move**
```
POST /games/{game_id}/move
Body: {
  "from_sq": int,
  "to_sq": int
}
```

**Undo Move**
```
POST /games/{game_id}/undo
```

#### AI Features

**Get Legal Moves**
```
GET /games/{game_id}/legal_moves
Response: [
  {"from": 81, "to": 72, "move_id": 123, ...}
]
```

**Get Best Move**
```
POST /games/{game_id}/best
Body: {
  "engine": "alphabeta" | "mcts" | "mcts_nn",
  "depth": int (for alphabeta),
  "sims": int (for mcts),
  "model_path": string (for mcts_nn)
}
Response: {
  "best": {"from": 81, "to": 72},
  "score": float,
  "pi": {...}
}
```

**Human-AI Play**
```
POST /games/{game_id}/human_ai
Body: {
  "human_move": "a0-a1",
  "engine": "mcts_nn",
  "sims": 200
}
Response: {
  "human": {...},
  "ai": {...},
  "state": {...}
}
```

#### Model Management

**List Models**
```
GET /model/list?dir=models
Response: {
  "models": ["latest.pt", ...]
}
```

**Get Model Info**
```
GET /model/info?model_path=models/latest.pt
Response: {
  "path": "...",
  "size_mb": 2.5,
  "parameters": 150000,
  "structure": [...]
}
```

**Get Model Framework**
```
GET /model/framework
Response: {
  "loaded": true,
  "path": "models/latest.pt",
  "framework": "generic" | "legacy"
}
```

#### Training & Evaluation

**Self-Play**
```
POST /selfplay
Body: {
  "engine": "mcts" | "mcts_nn",
  "games": 1,
  "sims": 200,
  "max_moves": 200
}
```

**Arena Evaluation**
```
POST /arena/run
Body: {
  "engine_a": "mcts_nn",
  "engine_b": "alphabeta",
  "model_a": "models/v1.pt",
  "params_a": {"sims": 200},
  "params_b": {"depth": 3},
  "n_games": 20
}
Response: {
  "elo_diff": 121.3,
  "win_rate": 0.675,
  "wins": 12,
  "draws": 3,
  "losses": 5
}
```

### Installation & Setup

#### Local Installation

**Prerequisites:**
```bash
# Python 3.10 or higher
python --version

# pip package manager
pip --version
```

**Install Dependencies:**
```bash
# Core dependencies
pip install torch torchvision  # PyTorch
pip install fastapi uvicorn    # API server
pip install numpy              # Numerical computing

# Optional: for GPU support
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**Quick Start:**

1. **Clone or download the project**

2. **Start the API server:**
```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

3. **Access the web interface:**
- Main game: http://127.0.0.1:8000/web/
- Model viewer: http://127.0.0.1:8000/web/model.html
- Arena: http://127.0.0.1:8000/web/arena.html

#### ☁️ Azure Cloud Deployment

For production deployment with GPU training on Azure cloud:

**Quick Deploy (10 minutes):**
```bash
cd deployment/azure/scripts
bash deploy_to_azure.sh
```

**Documentation:**
- 📖 [Azure Quick Start Guide](deployment/azure/docs/AZURE_QUICKSTART.md) - Start here!
- 📖 [Complete Deployment Guide](deployment/azure/docs/azure_deployment_guide.md) - Full details
- 📋 [Deployment Checklist](deployment/azure/docs/deployment_checklist.md) - Step-by-step
- 💰 Cost: ~$50/month (includes GPU training)

**Features:**
- One-click deployment to Azure App Service
- Automated GPU training on Azure VM
- Blob Storage for models and data
- Auto-scaling and monitoring
- Budget-friendly ($150/month plan included)

### Usage Examples

#### Example 1: Self-Play Training

```bash
# Step 1: Generate self-play data
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 50 \
    --sims 200 \
    --out data/selfplay_001.jsonl

# Step 2: Train the model
python scripts/train_generic.py \
    --game xiangqi \
    --data data/selfplay_001.jsonl \
    --model_out models/v1.pt \
    --epochs 10 \
    --batch_size 64 \
    --lr 0.001

# Step 3: Repeat with new model
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 50 \
    --sims 200 \
    --model models/v1.pt \
    --out data/selfplay_002.jsonl
```

#### Example 2: Model Evaluation

```bash
# Compare two models
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/v1.pt \
    --engine-b mcts_nn --model-b models/v2.pt \
    --games 20 \
    --output results.json

# Test against Alpha-Beta baseline
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt \
    --engine-b alphabeta --depth-b 3 \
    --games 20
```

#### Example 3: Human Play via API

```python
import requests

# Create game
response = requests.post('http://127.0.0.1:8000/api/games')
game_id = response.json()['game_id']

# Make human move and get AI response
response = requests.post(
    f'http://127.0.0.1:8000/api/games/{game_id}/human_ai',
    json={
        'human_move': 'b9-c7',  # Move knight
        'engine': 'mcts_nn',
        'sims': 200
    }
)

ai_move = response.json()['ai']
print(f"AI plays: {ai_move['from_coord']} → {ai_move['to_coord']}")
```

### Key Algorithms

#### 1. Move Generation (Pseudo-code)

```python
def generate_legal_moves(state):
    pseudo_legal = []
    
    # For each piece of current player
    for square, piece in enumerate(state.board):
        if piece.color != state.side_to_move:
            continue
            
        # Generate piece-specific moves
        if piece.type == PAWN:
            moves = generate_pawn_moves(square, piece)
        elif piece.type == CANNON:
            moves = generate_cannon_moves(square, piece)
        # ... other pieces
        
        pseudo_legal.extend(moves)
    
    # Filter illegal moves (king in check)
    legal = []
    for move in pseudo_legal:
        state.apply_move(move)
        if not state.is_in_check(opponent):
            legal.append(move)
        state.undo_move()
    
    return legal
```

#### 2. MCTS Selection (Pseudo-code)

```python
def select(node, state):
    while not node.is_leaf():
        # PUCT formula
        best_action = None
        best_value = -inf
        
        for action, child in node.children.items():
            q = child.value()  # Average value
            u = c_puct * child.prior * sqrt(node.visits) / (1 + child.visits)
            value = q + u
            
            if value > best_value:
                best_value = value
                best_action = action
        
        state.apply_move(best_action)
        node = node.children[best_action]
    
    return node, state
```

#### 3. Alpha-Beta Search (Pseudo-code)

```python
def alphabeta(state, depth, alpha, beta):
    # Terminal condition
    if depth == 0 or state.is_terminal():
        return evaluate(state)
    
    # Check transposition table
    tt_entry = tt.lookup(state.hash)
    if tt_entry and tt_entry.depth >= depth:
        return tt_entry.score
    
    # Move ordering
    moves = state.generate_legal_moves()
    moves = order_moves(moves, state)  # MVV/LVA, history, killer
    
    best_score = -infinity
    for move in moves:
        state.apply_move(move)
        score = -alphabeta(state, depth-1, -beta, -alpha)
        state.undo_move()
        
        best_score = max(best_score, score)
        alpha = max(alpha, score)
        
        if alpha >= beta:  # Beta cutoff
            record_killer(move)
            break
    
    # Store in transposition table
    tt.store(state.hash, depth, best_score)
    
    return best_score
```

### Performance Benchmarks

**Hardware:** Intel i7-10700K, 16GB RAM, CPU only

| Operation | Time | Notes |
|-----------|------|-------|
| Move Generation | < 1 ms | ~44 legal moves from start |
| Position Evaluation | < 0.1 ms | Material + basic heuristics |
| Alpha-Beta (depth=3) | ~2-5 s | With TT and move ordering |
| MCTS (200 sims) | ~5-10 s | With simple policy |
| MCTS+NN (200 sims) | ~15-30 s | With neural network |
| NN Inference | ~10 ms | Single position, CPU |
| Self-Play Game | ~2-5 min | MCTS, 200 sims, ~100 moves |

### Testing

Run integration tests:
```bash
python scripts/test_integration.py
```

**Test Coverage:**
- ✅ Import tests (legacy + generic)
- ✅ Legacy framework (XQNet, state, moves)
- ✅ Generic framework (GameInterface, MCTS, Trainer)
- ✅ Model compatibility (save/load)
- ✅ GameInterface implementation

### Extending to Other Games

The generic framework makes it easy to add new games:

```python
# games/go/game_adapter.py
from alphazero import GameInterface

class GoGame(GameInterface):
    def get_initial_state(self):
        return empty_19x19_board()
    
    def get_action_size(self):
        return 19 * 19 + 1  # +1 for pass
    
    def get_observation_shape(self):
        return (17, 19, 19)  # 8 history × 2 colors + side
    
    # Implement other abstract methods...

# Use with existing framework
game = GoGame()
model = PolicyValueNet(NetworkConfig(
    input_channels=17,
    board_height=19,
    board_width=19,
    action_size=362
))
```

### Future Enhancements

- [ ] GPU acceleration and batch inference
- [ ] Distributed self-play across multiple machines
- [ ] Opening book integration
- [ ] Endgame tablebase
- [ ] ELO rating system with SPRT
- [ ] Multi-game training (transfer learning)
- [ ] Mobile app (React Native)
- [ ] Tournament mode with Swiss pairing

### Technical Highlights (for Job Applications)

**Demonstrated Skills:**

1. **Deep Learning**
   - PyTorch neural network design and training
   - Policy-Value Network architecture
   - Residual connections and BatchNorm

2. **Reinforcement Learning**
   - AlphaZero algorithm implementation
   - Monte Carlo Tree Search
   - Self-play training pipeline

3. **Software Engineering**
   - Clean architecture with abstract interfaces
   - Modular design for extensibility
   - Comprehensive documentation

4. **Backend Development**
   - RESTful API with FastAPI
   - Asynchronous request handling
   - State management

5. **Frontend Development**
   - React components and hooks
   - Interactive game interface
   - Data visualization

6. **Algorithms**
   - Game tree search (Alpha-Beta, MCTS)
   - Heuristic optimization (TT, QS, move ordering)
   - Complex rule enforcement

7. **Testing & Quality**
   - Integration test suite
   - Model versioning and evaluation
   - Performance benchmarking

### License

This project is for educational and portfolio purposes.

### Contact

For job opportunities or technical discussions, please contact via GitHub.

---

<a name="chinese"></a>
## 中文文档

### 项目概述

**AlphaChess** 是一个完整实现的 AlphaZero 风格的中国象棋强化学习系统。该项目展示了先进的 AI 技术，包括蒙特卡洛树搜索（MCTS）、深度神经网络和自对弈训练，并配有现代化的 Web 应用和 REST API。

**核心特性：**
- 🎮 完整的象棋引擎，严格执行规则
- 🧠 AlphaZero 风格的神经网络（策略-价值网络）
- 🌲 使用 PUCT 算法的蒙特卡洛树搜索
- 🔍 带高级优化的 Alpha-Beta 搜索
- 🎯 自对弈训练流程，使用 JSONL 数据格式
- 🏆 竞技场/ELO 评测系统用于模型比较
- 🌐 基于 React 的现代 Web 界面
- 🔌 基于 FastAPI 的 RESTful API
- 🎨 模型可视化和检查工具
- 🔄 可扩展到其他棋类游戏的通用框架
- ☁️ Azure 云部署，配有自动化脚本

### 技术栈

**后端：**
- Python 3.10+
- PyTorch（深度学习）
- FastAPI（REST API）
- NumPy（数值计算）

**前端：**
- React 18
- Babel（JSX 编译）
- 现代 CSS3

**架构：**
- MVC（Model-View-Controller）
- 游戏无关的抽象接口设计
- 模块化架构，易于扩展

### 项目结构

```
alphachess/
├── xq/                          # 象棋游戏引擎
│   ├── constants.py            # 棋盘尺寸、棋子类型
│   ├── move.py                 # 32位走法编码
│   ├── zobrist.py              # 局面的 Zobrist 哈希
│   ├── state.py                # 核心游戏逻辑（800+ 行）
│   ├── policy.py               # 神经网络的走法索引
│   ├── nn.py                   # 传统神经网络
│   ├── mcts.py                 # MCTS 实现
│   ├── selfplay.py             # 自对弈数据生成
│   ├── game_adapter.py         # GameInterface 适配器
│   └── search/
│       └── alpha_beta.py       # Alpha-Beta 搜索（TT、QS）
│
├── alphazero/                   # 通用 AlphaZero 框架
│   ├── game_interface.py       # 抽象游戏接口
│   ├── network.py              # 通用 PolicyValueNet
│   ├── mcts_generic.py         # 游戏无关的 MCTS
│   └── trainer.py              # 通用训练流程
│
├── api/
│   └── server.py               # FastAPI REST API（770+ 行）
│
├── web/                         # React 前端
│   ├── index.html              # 主游戏界面
│   ├── app.js                  # 游戏 UI 逻辑
│   ├── arena.html              # 竞技场评测
│   ├── arena.js                # 竞技场 UI 逻辑
│   ├── model.html              # 模型查看器
│   └── model.js                # 模型检查
│
├── scripts/                     # CLI 工具
│   ├── train.py                # 传统训练
│   ├── train_generic.py        # 通用训练
│   ├── self_play.py            # 传统自对弈
│   ├── self_play_generic.py    # 通用自对弈
│   ├── arena.py                # ELO 评测
│   └── test_integration.py     # 集成测试
│
└── docs/                        # 文档
    ├── README_FRAMEWORK.md     # 架构详情
    ├── MIGRATION_GUIDE.md      # 迁移指南
    ├── VERSION_COMPARISON.md   # 版本对比
    ├── ARENA_GUIDE.md          # 竞技场使用指南
    └── CHANGELOG.md            # 版本历史
```

### 核心组件

#### 1. 游戏引擎（`xq/state.py`）

系统的核心，实现完整的象棋规则：

**主要特性：**
- 使用有符号整数的 9×10 棋盘表示
- 增量式走法应用，支持撤销
- Zobrist 哈希用于快速局面查找
- 伪合法和合法走法生成
- 将军检测和将死判定
- 三次重复检测
- 中国象棋特定规则：
  - 将、士的九宫限制
  - 兵过河后的走法
  - 炮的跳吃机制
  - 马的蹩腿检测
  - 将帅照面规则
  - 长将/长捉检测

**性能：**
- 初始局面约 44 个合法走法
- 亚毫秒级走法生成
- O(1) 局面查找（Zobrist 哈希）

#### 2. 神经网络架构

**输入表示：**
- 15 通道 × 10 行 × 9 列
- 通道：14 种棋子（7 种 × 2 色）+ 1 行棋方

**网络架构（通用版）：**
```
输入 (15, 10, 9)
    ↓
Conv2d(3×3) + BatchNorm + ReLU
    ↓
N × 残差块
    ↓
┌──────────────┬──────────────┐
│  策略头      │   价值头     │
│              │              │
│ Conv(1×1)    │  Conv(1×1)   │
│ + BatchNorm  │  + BatchNorm │
│ + Flatten    │  + Flatten   │
│ + Linear     │  + Linear    │
│              │  + Tanh      │
│ (8100 维)    │  (标量)      │
└──────────────┴──────────────┘
```

**关键参数：**
- `hidden_channels`: 64（默认），128（高级）
- `num_res_blocks`: 3（默认），7-10（高级）
- 动作空间：8100（90×90 起点-终点）
- 价值范围：[-1, 1]（输到赢）

**网络类型：**
1. **传统 XQNet**：无 BatchNorm 的简单 CNN
2. **通用 PolicyValueNet**：带 BatchNorm 的现代架构

#### 3. 搜索算法

##### 蒙特卡洛树搜索（MCTS）

**算法：** PUCT（预测器 + 树的置信上界）

**公式：**
$$ UCT = Q(s,a) + c\_puct × P(s,a) × \frac{\sqrt{N(s)}} {(1 + N(s,a))} $$

**特性：**
- Dirichlet 噪声用于探索（α=0.3）
- 温度参数控制动作选择
- 虚拟损失支持并行搜索
- 合法走法掩码

**参数：**
- `num_simulations`: 100-800（默认：200）
- `c_puct`: 1.5（探索常数）
- `temperature`: 1.0（探索）→ 0.1（利用）

##### Alpha-Beta 搜索

**特性：**
- Negamax 框架
- 使用 Zobrist 哈希的置换表（TT）
- 静态搜索确保战术稳定性
- 走法排序：
  - MVV/LVA（最有价值受害者/最低价值攻击者）
  - 历史启发
  - 杀手走法

**参数：**
- `depth`: 3-6（默认：3）
- `tt_size_mb`: 256（置换表大小）

#### 4. 训练流程

**自对弈过程：**
```
1. 从初始局面开始
2. 对于每步棋：
   - 运行 MCTS（加 Dirichlet 噪声）
   - 基于访问次数采样动作
   - 应用走法
3. 记录（状态、策略、价值）三元组
4. 继续直到游戏结束
5. 为所有局面分配最终结果
6. 保存为 JSONL 格式
```

**训练过程：**
```
1. 从 JSONL 加载自对弈数据
2. 创建 PyTorch DataLoader
3. 对于每个 epoch：
   - 前向传播：预测策略和价值
   - 损失 = CrossEntropy(策略) + MSE(价值)
   - 反向传播并优化
4. 保存检查点
```

**数据格式（JSONL）：**
```json
{
  "game_id": 0,
  "result": 1,
  "records": [
    {
      "planes": [[...], ...],  // 15×90 棋盘状态
      "pi": {"123": 0.15, ...}, // 策略分布
      "z": 1.0                  // 游戏结果
    }
  ],
  "timestamp": "2025-11-05T..."
}
```

### REST API 参考

基础 URL：`http://127.0.0.1:8000/api`

#### 游戏管理

**创建游戏**
```
POST /games
Body: {
  "squares": [int] (可选),
  "side_to_move": int (可选)
}
Response: {
  "game_id": "uuid",
  "state": {...}
}
```

**获取游戏状态**
```
GET /games/{game_id}
Response: {
  "board": [int],
  "side_to_move": int,
  "legal_moves": [...]
}
```

**走棋**
```
POST /games/{game_id}/move
Body: {
  "from_sq": int,
  "to_sq": int
}
```

**悔棋**
```
POST /games/{game_id}/undo
```

#### AI 功能

**获取合法走法**
```
GET /games/{game_id}/legal_moves
Response: [
  {"from": 81, "to": 72, "move_id": 123, ...}
]
```

**获取最佳走法**
```
POST /games/{game_id}/best
Body: {
  "engine": "alphabeta" | "mcts" | "mcts_nn",
  "depth": int (Alpha-Beta 用),
  "sims": int (MCTS 用),
  "model_path": string (MCTS+NN 用)
}
Response: {
  "best": {"from": 81, "to": 72},
  "score": float,
  "pi": {...}
}
```

**人机对战**
```
POST /games/{game_id}/human_ai
Body: {
  "human_move": "a0-a1",
  "engine": "mcts_nn",
  "sims": 200
}
Response: {
  "human": {...},
  "ai": {...},
  "state": {...}
}
```

#### 模型管理

**列出模型**
```
GET /model/list?dir=models
Response: {
  "models": ["latest.pt", ...]
}
```

**获取模型信息**
```
GET /model/info?model_path=models/latest.pt
Response: {
  "path": "...",
  "size_mb": 2.5,
  "parameters": 150000,
  "structure": [...]
}
```

**获取模型框架**
```
GET /model/framework
Response: {
  "loaded": true,
  "path": "models/latest.pt",
  "framework": "generic" | "legacy"
}
```

#### 训练与评测

**自对弈**
```
POST /selfplay
Body: {
  "engine": "mcts" | "mcts_nn",
  "games": 1,
  "sims": 200,
  "max_moves": 200
}
```

**竞技场评测**
```
POST /arena/run
Body: {
  "engine_a": "mcts_nn",
  "engine_b": "alphabeta",
  "model_a": "models/v1.pt",
  "params_a": {"sims": 200},
  "params_b": {"depth": 3},
  "n_games": 20
}
Response: {
  "elo_diff": 121.3,
  "win_rate": 0.675,
  "wins": 12,
  "draws": 3,
  "losses": 5
}
```

### 安装与设置

#### 本地安装

**前置要求：**
```bash
# Python 3.10 或更高版本
python --version

# pip 包管理器
pip --version
```

**安装依赖：**
```bash
# 核心依赖
pip install torch torchvision  # PyTorch
pip install fastapi uvicorn    # API 服务器
pip install numpy              # 数值计算

# 可选：GPU 支持
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**快速开始：**

1. **克隆或下载项目**

2. **启动 API 服务器：**
```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

3. **访问 Web 界面：**
- 主游戏：http://127.0.0.1:8000/web/
- 模型查看器：http://127.0.0.1:8000/web/model.html
- 竞技场：http://127.0.0.1:8000/web/arena.html

#### ☁️ Azure 云部署

生产环境部署，支持 GPU 训练：

**快速部署（10 分钟）：**
```bash
cd deployment/azure/scripts
bash deploy_to_azure.sh
```

**文档资源：**
- 📖 [Azure 快速开始指南](deployment/azure/docs/AZURE_QUICKSTART.md) - 从这里开始！
- 📖 [完整部署指南](deployment/azure/docs/azure_deployment_guide.md) - 详细说明
- 📋 [部署检查清单](deployment/azure/docs/deployment_checklist.md) - 分步指导
- 💰 成本：约 $50/月（包含 GPU 训练）

**特性：**
- 一键部署到 Azure App Service
- Azure VM 上自动化 GPU 训练
- Blob Storage 存储模型和数据
- 自动扩展和监控
- 预算友好（包含 $150/月方案）

### 使用示例

#### 示例 1：自对弈训练

```bash
# 步骤 1：生成自对弈数据
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 50 \
    --sims 200 \
    --out data/selfplay_001.jsonl

# 步骤 2：训练模型
python scripts/train_generic.py \
    --game xiangqi \
    --data data/selfplay_001.jsonl \
    --model_out models/v1.pt \
    --epochs 10 \
    --batch_size 64 \
    --lr 0.001

# 步骤 3：使用新模型重复
python scripts/self_play_generic.py \
    --game xiangqi \
    --games 50 \
    --sims 200 \
    --model models/v1.pt \
    --out data/selfplay_002.jsonl
```

#### 示例 2：模型评测

```bash
# 比较两个模型
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/v1.pt \
    --engine-b mcts_nn --model-b models/v2.pt \
    --games 20 \
    --output results.json

# 与 Alpha-Beta 基准测试
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt \
    --engine-b alphabeta --depth-b 3 \
    --games 20
```

#### 示例 3：通过 API 进行人机对战

```python
import requests

# 创建游戏
response = requests.post('http://127.0.0.1:8000/api/games')
game_id = response.json()['game_id']

# 走棋并获取 AI 回应
response = requests.post(
    f'http://127.0.0.1:8000/api/games/{game_id}/human_ai',
    json={
        'human_move': 'b9-c7',  # 跳马
        'engine': 'mcts_nn',
        'sims': 200
    }
)

ai_move = response.json()['ai']
print(f"AI 走棋：{ai_move['from_coord']} → {ai_move['to_coord']}")
```

### 关键算法

#### 1. 走法生成（伪代码）

```python
def generate_legal_moves(state):
    pseudo_legal = []
    
    # 遍历当前玩家的每个棋子
    for square, piece in enumerate(state.board):
        if piece.color != state.side_to_move:
            continue
            
        # 生成特定棋子的走法
        if piece.type == PAWN:
            moves = generate_pawn_moves(square, piece)
        elif piece.type == CANNON:
            moves = generate_cannon_moves(square, piece)
        # ... 其他棋子
        
        pseudo_legal.extend(moves)
    
    # 过滤非法走法（将军）
    legal = []
    for move in pseudo_legal:
        state.apply_move(move)
        if not state.is_in_check(opponent):
            legal.append(move)
        state.undo_move()
    
    return legal
```

#### 2. MCTS 选择（伪代码）

```python
def select(node, state):
    while not node.is_leaf():
        # PUCT 公式
        best_action = None
        best_value = -inf
        
        for action, child in node.children.items():
            q = child.value()  # 平均价值
            u = c_puct * child.prior * sqrt(node.visits) / (1 + child.visits)
            value = q + u
            
            if value > best_value:
                best_value = value
                best_action = action
        
        state.apply_move(best_action)
        node = node.children[best_action]
    
    return node, state
```

#### 3. Alpha-Beta 搜索（伪代码）

```python
def alphabeta(state, depth, alpha, beta):
    # 终止条件
    if depth == 0 or state.is_terminal():
        return evaluate(state)
    
    # 查询置换表
    tt_entry = tt.lookup(state.hash)
    if tt_entry and tt_entry.depth >= depth:
        return tt_entry.score
    
    # 走法排序
    moves = state.generate_legal_moves()
    moves = order_moves(moves, state)  # MVV/LVA、历史、杀手
    
    best_score = -infinity
    for move in moves:
        state.apply_move(move)
        score = -alphabeta(state, depth-1, -beta, -alpha)
        state.undo_move()
        
        best_score = max(best_score, score)
        alpha = max(alpha, score)
        
        if alpha >= beta:  # Beta 剪枝
            record_killer(move)
            break
    
    # 存入置换表
    tt.store(state.hash, depth, best_score)
    
    return best_score
```

### 性能基准

**硬件：** Intel i7-10700K, 16GB RAM, 仅 CPU

| 操作 | 时间 | 备注 |
|------|------|------|
| 走法生成 | < 1 ms | 初始局面约 44 个合法走法 |
| 局面评估 | < 0.1 ms | 子力 + 基本启发 |
| Alpha-Beta（深度=3） | ~2-5 秒 | 带 TT 和走法排序 |
| MCTS（200 模拟） | ~5-10 秒 | 简单策略 |
| MCTS+NN（200 模拟） | ~15-30 秒 | 神经网络 |
| NN 推理 | ~10 ms | 单个局面，CPU |
| 自对弈对局 | ~2-5 分钟 | MCTS，200 模拟，约 100 步 |

### 测试

运行集成测试：
```bash
python scripts/test_integration.py
```

**测试覆盖：**
- ✅ 导入测试（传统 + 通用）
- ✅ 传统框架（XQNet、状态、走法）
- ✅ 通用框架（GameInterface、MCTS、Trainer）
- ✅ 模型兼容性（保存/加载）
- ✅ GameInterface 实现

### 扩展到其他游戏

通用框架使添加新游戏变得简单：

```python
# games/go/game_adapter.py
from alphazero import GameInterface

class GoGame(GameInterface):
    def get_initial_state(self):
        return empty_19x19_board()
    
    def get_action_size(self):
        return 19 * 19 + 1  # +1 表示 pass
    
    def get_observation_shape(self):
        return (17, 19, 19)  # 8 历史 × 2 色 + 行棋方
    
    # 实现其他抽象方法...

# 与现有框架配合使用
game = GoGame()
model = PolicyValueNet(NetworkConfig(
    input_channels=17,
    board_height=19,
    board_width=19,
    action_size=362
))
```

### 未来增强

- [ ] GPU 加速和批量推理
- [ ] 跨多台机器的分布式自对弈
- [ ] 开局库集成
- [ ] 残局数据库
- [ ] 带 SPRT 的 ELO 评级系统
- [ ] 多游戏训练（迁移学习）
- [ ] 移动应用（React Native）
- [ ] 瑞士制配对的锦标赛模式

### 技术亮点（求职用）

**展示的技能：**

1. **深度学习**
   - PyTorch 神经网络设计和训练
   - 策略-价值网络架构
   - 残差连接和 BatchNorm

2. **强化学习**
   - AlphaZero 算法实现
   - 蒙特卡洛树搜索
   - 自对弈训练流程

3. **软件工程**
   - 带抽象接口的清晰架构
   - 模块化设计便于扩展
   - 全面的文档

4. **后端开发**
   - 使用 FastAPI 的 RESTful API
   - 异步请求处理
   - 状态管理

5. **前端开发**
   - React 组件和 hooks
   - 交互式游戏界面
   - 数据可视化

6. **算法**
   - 博弈树搜索（Alpha-Beta、MCTS）
   - 启发式优化（TT、QS、走法排序）
   - 复杂规则执行

7. **测试与质量**
   - 集成测试套件
   - 模型版本控制和评估
   - 性能基准测试

### 许可证

本项目用于教育和作品集目的。

### 联系方式

如有工作机会或技术讨论，请通过 GitHub 联系。

---

**项目完成度：100%**  
**代码行数：~5000+ 行**  
**文档：完整的中英文文档**  
**测试覆盖：集成测试全部通过**



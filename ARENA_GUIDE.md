# Arena/ELO 评测指南

## 概述

Arena（竞技场）功能用于比较两个引擎或模型的强度，通过让它们对战多局并计算 ELO 分差来评估相对实力。

## 功能特性

- ✅ 支持多种引擎类型（random, alphabeta, mcts, mcts_nn）
- ✅ 自动换色对战确保公平性
- ✅ 完整的 ELO 计算
- ✅ CLI 和 Web 双界面
- ✅ 详细的对局记录和统计

## 使用方式

### 方式 1：Web 界面（推荐）

1. 启动服务器：
```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

2. 访问竞技场页面：
```
http://127.0.0.1:8000/web/arena.html
```

3. 配置对战参数：
   - **玩家 A**：选择引擎类型、模型路径、参数
   - **玩家 B**：选择引擎类型、模型路径、参数
   - **对战局数**：必须是偶数（各执红黑各半）

4. 点击"开始对战"

5. 查看结果：
   - ELO 分差（正值表示 A 强，负值表示 B 强）
   - 胜率统计
   - 每局详细结果

### 方式 2：命令行 (CLI)

#### 基本用法

```bash
python scripts/arena.py \
    --engine-a <引擎类型> \
    --engine-b <引擎类型> \
    --games <对战局数>
```

#### 示例 1：比较两个 MCTS+NN 模型

```bash
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/v1.pt \
    --engine-b mcts_nn --model-b models/v2.pt \
    --games 20 \
    --output results.json
```

#### 示例 2：测试 Alpha-Beta vs MCTS

```bash
python scripts/arena.py \
    --engine-a alphabeta --depth-a 4 \
    --engine-b mcts --sims-b 400 \
    --games 10 \
    --verbose
```

#### 示例 3：MCTS+NN vs Alpha-Beta

```bash
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt --sims-a 200 \
    --engine-b alphabeta --depth-b 3 \
    --games 20
```

#### 示例 4：测试基准（vs 随机）

```bash
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt \
    --engine-b random \
    --games 10
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--engine-a` | 玩家 A 引擎类型 | random, alphabeta, mcts, mcts_nn | random |
| `--engine-b` | 玩家 B 引擎类型 | random, alphabeta, mcts, mcts_nn | random |
| `--model-a` | 玩家 A 模型路径 | 文件路径 | None |
| `--model-b` | 玩家 B 模型路径 | 文件路径 | None |
| `--depth-a` | 玩家 A 搜索深度（Alpha-Beta） | 1-8 | 3 |
| `--depth-b` | 玩家 B 搜索深度（Alpha-Beta） | 1-8 | 3 |
| `--sims-a` | 玩家 A MCTS 模拟次数 | 10-2000 | 200 |
| `--sims-b` | 玩家 B MCTS 模拟次数 | 10-2000 | 200 |
| `--games` | 总对战局数（必须为偶数） | 2-100 | 20 |
| `--output` | 结果保存路径（JSON） | 文件路径 | None |
| `--verbose` | 显示详细进度 | - | False |

## 引擎类型说明

### 1. random（随机）
- 从合法走法中随机选择
- 用于测试基准
- 不需要额外参数

### 2. alphabeta（Alpha-Beta 搜索）
- 传统搜索算法
- 参数：`--depth-a` 或 `--depth-b`（搜索深度）
- 推荐深度：3-5（更高会很慢）

### 3. mcts（MCTS）
- 蒙特卡洛树搜索
- 参数：`--sims-a` 或 `--sims-b`（模拟次数）
- 推荐模拟次数：100-400

### 4. mcts_nn（MCTS + 神经网络）
- AlphaZero 风格
- 参数：
  - `--model-a` 或 `--model-b`（模型路径）
  - `--sims-a` 或 `--sims-b`（模拟次数）
- 自动检测模型类型（legacy/generic）

## 结果解读

### ELO 分差

ELO 分差表示玩家 A 相对于玩家 B 的强度差异：

- **+100 ELO**：A 约有 64% 的胜率
- **+200 ELO**：A 约有 76% 的胜率
- **+400 ELO**：A 约有 91% 的胜率
- **0 ELO**：两者实力相当
- **负值**：B 比 A 强

### 统计显著性

对战局数越多，结果越可靠：

- **10 局**：初步测试
- **20 局**：基本可靠
- **50 局**：较为可靠
- **100 局**：非常可靠

建议至少进行 20 局对战。

## 输出格式

### CLI 输出示例

```
============================================================
Arena/ELO Evaluation
============================================================
Player A: mcts_nn
  Model: models/v1.pt
Player B: mcts_nn
  Model: models/v2.pt
Games: 20 (each color: 10)
============================================================

Game 1/20: A(RED) vs B(BLACK)... A wins (45 moves)
Game 2/20: A(RED) vs B(BLACK)... Draw (120 moves)
...

============================================================
Results
============================================================
Player A: mcts_nn
  Wins: 12
  Draws: 3
  Losses: 5
  Win Rate: 67.50%
  ELO Difference: +121.3 (A - B)
============================================================
[OK] Player A is stronger by ~121 ELO points
```

### JSON 输出格式

```json
{
  "engine_a": "mcts_nn",
  "engine_b": "mcts_nn",
  "model_a": "models/v1.pt",
  "model_b": "models/v2.pt",
  "n_games": 20,
  "elo_diff": 121.3,
  "win_rate": 0.675,
  "wins": 12,
  "draws": 3,
  "losses": 5,
  "scores": [1.0, 0.5, 1.0, ...],
  "games": [
    {
      "game_number": 1,
      "red": "A",
      "black": "B",
      "result": 1,
      "outcome": "A wins",
      "moves": 45
    },
    ...
  ],
  "timestamp": "2025-11-05T12:34:56"
}
```

## 常见用例

### 1. 模型选择（Model Selection）

训练多个模型后，选择最强的：

```bash
# 比较 v1 vs v2
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/v1.pt \
    --engine-b mcts_nn --model-b models/v2.pt \
    --games 30

# 比较 v2 vs v3
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/v2.pt \
    --engine-b mcts_nn --model-b models/v3.pt \
    --games 30
```

### 2. 训练进度评估

定期与基准模型对战，跟踪训练进度：

```bash
# 与初始模型对战
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt \
    --engine-b mcts_nn --model-b models/baseline.pt \
    --games 20 \
    --output progress_$(date +%Y%m%d).json
```

### 3. 算法比较

比较不同搜索算法的效果：

```bash
# MCTS+NN vs Alpha-Beta
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt --sims-a 200 \
    --engine-b alphabeta --depth-b 4 \
    --games 20
```

### 4. 参数调优

测试不同的 MCTS 模拟次数：

```bash
# 200 sims vs 400 sims
python scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt --sims-a 200 \
    --engine-b mcts_nn --model-b models/latest.pt --sims-b 400 \
    --games 20
```

## 性能注意事项

### 预计耗时

对战时间取决于引擎类型和参数：

| 配置 | 单局耗时 | 20 局总耗时 |
|------|---------|-------------|
| random vs random | ~1 秒 | ~20 秒 |
| alphabeta(d=3) vs alphabeta(d=3) | ~5 秒 | ~2 分钟 |
| mcts(s=200) vs mcts(s=200) | ~10 秒 | ~3 分钟 |
| mcts_nn(s=200) vs mcts_nn(s=200) | ~30 秒 | ~10 分钟 |

**建议**：
- 初步测试：10 局
- 正式评测：20-50 局
- 发布前验证：100 局

### 性能优化

1. **减少模拟次数**：对于快速测试，使用较少的 MCTS 模拟次数
2. **使用 Alpha-Beta**：如果不需要 NN，Alpha-Beta 更快
3. **并行评测**：可以同时运行多个 arena 实例（不同终端）

## API 集成

在你的 Python 代码中使用 Arena：

```python
from scripts.arena import arena

results = arena(
    engine_a='mcts_nn',
    engine_b='alphabeta',
    model_a='models/v1.pt',
    model_b=None,
    params_a={'sims': 200},
    params_b={'depth': 3},
    n_games=20,
    verbose=True
)

print(f"ELO Diff: {results['elo_diff']:+.1f}")
print(f"Win Rate: {results['win_rate']*100:.1f}%")
```

## 故障排除

### 问题 1：模型加载失败

**错误**：`Failed to load model`

**解决**：
- 检查模型文件是否存在
- 确认模型路径正确
- 验证模型格式（.pt 文件）

### 问题 2：对战非常慢

**原因**：MCTS 模拟次数过高或搜索深度过大

**解决**：
- 减少 `--sims-a` 和 `--sims-b`（建议 100-200）
- 减少 `--depth-a` 和 `--depth-b`（建议 3-4）

### 问题 3：结果不稳定

**原因**：对战局数太少

**解决**：
- 增加 `--games` 到至少 20 局
- 对于重要评测，建议 50 局以上

## 最佳实践

1. **始终换色对战**：脚本自动处理，确保公平性
2. **使用足够的对战局数**：至少 20 局
3. **保存结果**：使用 `--output` 保存为 JSON，便于后续分析
4. **设置合理的参数**：避免过高的搜索深度或模拟次数
5. **定期评测**：训练过程中定期运行 Arena 跟踪进度

## 相关链接

- [README_FRAMEWORK.md](README_FRAMEWORK.md) - 框架架构说明
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 迁移指南
- [VERSION_COMPARISON.md](VERSION_COMPARISON.md) - 版本对比

## 技术参考

ELO 计算公式：

```
P(A wins) = 1 / (1 + 10^((ELO_B - ELO_A) / 400))

ELO_diff = -400 * log10(1 / win_rate - 1)
```

其中 `win_rate` 是 A 的得分率（胜=1, 和=0.5, 负=0）。


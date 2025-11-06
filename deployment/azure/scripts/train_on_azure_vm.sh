#!/bin/bash
# Azure GPU VM 训练脚本
# 此脚本用于在 Azure GPU VM 上进行神经网络训练

set -e

echo "🧠 AlphaChess Azure GPU 训练脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ===========================
# 配置参数
# ===========================
GAMES=${GAMES:-100}              # 自对弈局数
SIMS=${SIMS:-400}                # MCTS 模拟次数
EPOCHS=${EPOCHS:-20}             # 训练轮数
BATCH_SIZE=${BATCH_SIZE:-128}   # 批大小
LEARNING_RATE=${LR:-0.001}      # 学习率
MODEL_NAME=${MODEL_NAME:-"latest.pt"}

# Azure Storage 配置（从环境变量读取）
STORAGE_ACCOUNT=${AZURE_STORAGE_ACCOUNT:-""}
STORAGE_KEY=${AZURE_STORAGE_KEY:-""}

echo "训练参数:"
echo "  自对弈局数: $GAMES"
echo "  MCTS 模拟: $SIMS"
echo "  训练轮数: $EPOCHS"
echo "  批大小: $BATCH_SIZE"
echo "  学习率: $LEARNING_RATE"
echo ""

# ===========================
# 1. 环境检查
# ===========================
echo "📋 步骤 1: 检查环境..."

# 检查 CUDA
if command -v nvidia-smi &> /dev/null; then
  echo "✅ 检测到 NVIDIA GPU:"
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
  echo "⚠️  未检测到 GPU，将使用 CPU 训练（速度较慢）"
fi

# 检查 Python 和依赖
python3 --version
pip3 list | grep -E "torch|fastapi|numpy"

# ===========================
# 2. 下载当前模型（如果存在）
# ===========================
echo ""
echo "📥 步骤 2: 从 Azure Blob 下载当前模型..."

if [ -n "$STORAGE_ACCOUNT" ] && [ -n "$STORAGE_KEY" ]; then
  mkdir -p models
  
  # 尝试下载现有模型
  az storage blob download \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --container-name models \
    --name $MODEL_NAME \
    --file models/$MODEL_NAME \
    2>/dev/null && echo "✅ 模型下载成功" || echo "ℹ️  未找到现有模型，将从头训练"
else
  echo "⚠️  未配置 Azure Storage，跳过模型下载"
fi

# ===========================
# 3. 生成自对弈数据
# ===========================
echo ""
echo "🎮 步骤 3: 生成自对弈数据..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATA_FILE="data/selfplay_$TIMESTAMP.jsonl"

mkdir -p data

python3 scripts/self_play_generic.py \
  --game xiangqi \
  --games $GAMES \
  --sims $SIMS \
  --model models/$MODEL_NAME \
  --out $DATA_FILE \
  --max_moves 200

echo "✅ 自对弈完成，数据保存到: $DATA_FILE"

# 统计数据
NUM_GAMES=$(grep -c '^{' $DATA_FILE || echo "0")
echo "  生成对局数: $NUM_GAMES"

# ===========================
# 4. 训练神经网络
# ===========================
echo ""
echo "🔥 步骤 4: 训练神经网络..."

NEW_MODEL="models/model_$TIMESTAMP.pt"

python3 scripts/train_generic.py \
  --game xiangqi \
  --data $DATA_FILE \
  --model_in models/$MODEL_NAME \
  --model_out $NEW_MODEL \
  --epochs $EPOCHS \
  --batch_size $BATCH_SIZE \
  --lr $LEARNING_RATE \
  --device cuda

echo "✅ 训练完成，模型保存到: $NEW_MODEL"

# ===========================
# 5. 更新 latest.pt
# ===========================
echo ""
echo "🔄 步骤 5: 更新 latest.pt..."
cp $NEW_MODEL models/latest.pt
echo "✅ latest.pt 已更新"

# ===========================
# 6. 上传到 Azure Blob Storage
# ===========================
echo ""
echo "📤 步骤 6: 上传模型到 Azure Blob Storage..."

if [ -n "$STORAGE_ACCOUNT" ] && [ -n "$STORAGE_KEY" ]; then
  # 上传新模型
  az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --container-name models \
    --name "model_$TIMESTAMP.pt" \
    --file $NEW_MODEL \
    --overwrite
  
  # 更新 latest.pt
  az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --container-name models \
    --name latest.pt \
    --file models/latest.pt \
    --overwrite
  
  # 上传训练数据
  az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --container-name data \
    --name "selfplay_$TIMESTAMP.jsonl" \
    --file $DATA_FILE \
    --overwrite
  
  echo "✅ 所有文件上传完成"
else
  echo "⚠️  未配置 Azure Storage，跳过上传"
fi

# ===========================
# 7. 清理本地文件（可选）
# ===========================
echo ""
echo "🧹 步骤 7: 清理临时文件..."

# 保留最新的 3 个模型
ls -t models/model_*.pt | tail -n +4 | xargs -r rm
echo "✅ 清理完成"

# ===========================
# 8. 模型评估（可选）
# ===========================
echo ""
echo "📊 步骤 8: 评估新模型（可选）..."

# 与之前的模型对战
if [ -f "models/model_old.pt" ]; then
  echo "运行 Arena 评测..."
  python3 scripts/arena.py \
    --engine-a mcts_nn --model-a models/latest.pt \
    --engine-b mcts_nn --model-b models/model_old.pt \
    --games 20 \
    --output arena_result_$TIMESTAMP.json
  
  echo "✅ 评测完成，结果保存到: arena_result_$TIMESTAMP.json"
else
  echo "ℹ️  未找到旧模型，跳过评测"
fi

# ===========================
# 完成
# ===========================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 训练流程完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 训练摘要："
echo "  自对弈对局: $NUM_GAMES"
echo "  训练轮数: $EPOCHS"
echo "  新模型: $NEW_MODEL"
echo "  数据文件: $DATA_FILE"
echo ""
echo "🎯 下一步："
echo "  1. 在 Web 界面测试新模型"
echo "  2. 运行 Arena 评测"
echo "  3. 如果满意，继续下一轮训练"
echo ""

# 发送通知（可选，需要配置）
if [ -n "$NOTIFICATION_WEBHOOK" ]; then
  curl -X POST $NOTIFICATION_WEBHOOK \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✅ AlphaChess 训练完成！模型: $NEW_MODEL\"}"
fi

echo "🚀 训练脚本执行完毕！"


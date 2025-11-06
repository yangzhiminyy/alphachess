#!/bin/bash
# Azure GPU VM 环境配置脚本
# 在新创建的 Azure GPU VM 上运行此脚本以配置训练环境

set -e

echo "⚙️  AlphaChess Azure GPU VM 环境配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ===========================
# 1. 系统更新
# ===========================
echo ""
echo "📦 步骤 1: 更新系统软件包..."
sudo apt update
sudo apt upgrade -y

# ===========================
# 2. 安装基础工具
# ===========================
echo ""
echo "🛠️  步骤 2: 安装基础工具..."
sudo apt install -y \
  build-essential \
  git \
  wget \
  curl \
  vim \
  htop \
  tmux \
  zip \
  unzip

# ===========================
# 3. 安装 Python 和 pip
# ===========================
echo ""
echo "🐍 步骤 3: 安装 Python 3.10..."
sudo apt install -y python3.10 python3.10-venv python3-pip

# 更新 pip
python3 -m pip install --upgrade pip

# ===========================
# 4. 安装 CUDA 和 cuDNN（如果需要）
# ===========================
echo ""
echo "🎮 步骤 4: 检查 NVIDIA 驱动和 CUDA..."

if command -v nvidia-smi &> /dev/null; then
  echo "✅ NVIDIA 驱动已安装:"
  nvidia-smi
  
  # 安装 CUDA Toolkit（如果未安装）
  if ! command -v nvcc &> /dev/null; then
    echo "安装 CUDA Toolkit 11.8..."
    wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run
    sudo sh cuda_11.8.0_520.61.05_linux.run --silent --toolkit
    
    # 配置环境变量
    echo 'export PATH=/usr/local/cuda-11.8/bin:$PATH' >> ~/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
    source ~/.bashrc
  fi
else
  echo "⚠️  未检测到 NVIDIA GPU，将使用 CPU 训练"
fi

# ===========================
# 5. 安装 PyTorch 和依赖
# ===========================
echo ""
echo "🔥 步骤 5: 安装 PyTorch 和依赖..."

# 检测 CUDA 版本
if command -v nvcc &> /dev/null; then
  echo "使用 CUDA 11.8 版本的 PyTorch"
  pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
  echo "安装 CPU 版本的 PyTorch"
  pip3 install torch torchvision torchaudio
fi

# 安装其他依赖
pip3 install fastapi uvicorn numpy

# ===========================
# 6. 安装 Azure CLI
# ===========================
echo ""
echo "☁️  步骤 6: 安装 Azure CLI..."
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# ===========================
# 7. 克隆 AlphaChess 代码
# ===========================
echo ""
echo "📥 步骤 7: 克隆 AlphaChess 代码..."

read -p "请输入 Git 仓库 URL (回车跳过): " GIT_REPO
if [ -n "$GIT_REPO" ]; then
  git clone $GIT_REPO ~/alphachess
  cd ~/alphachess
  pip3 install -r requirements.txt
  echo "✅ 代码克隆完成"
else
  echo "ℹ️  跳过代码克隆，请手动上传代码"
fi

# ===========================
# 8. 配置 Azure Storage
# ===========================
echo ""
echo "💾 步骤 8: 配置 Azure Storage..."

read -p "Azure Storage 账户名: " STORAGE_ACCOUNT
read -p "Azure Storage 密钥: " STORAGE_KEY

if [ -n "$STORAGE_ACCOUNT" ] && [ -n "$STORAGE_KEY" ]; then
  cat >> ~/.bashrc <<EOF

# Azure Storage 配置
export AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT"
export AZURE_STORAGE_KEY="$STORAGE_KEY"
EOF
  
  source ~/.bashrc
  
  echo "✅ Azure Storage 配置完成"
  
  # 登录 Azure CLI
  echo "登录 Azure CLI..."
  az login
else
  echo "ℹ️  跳过 Azure Storage 配置"
fi

# ===========================
# 9. 创建工作目录
# ===========================
echo ""
echo "📁 步骤 9: 创建工作目录..."

mkdir -p ~/alphachess/models
mkdir -p ~/alphachess/data
mkdir -p ~/alphachess/logs

# ===========================
# 10. 配置自动关机（可选）
# ===========================
echo ""
echo "⏰步骤 10: 配置自动关机（节省成本）..."

read -p "是否配置训练完成后自动关机？(y/n): " AUTO_SHUTDOWN
if [ "$AUTO_SHUTDOWN" = "y" ]; then
  cat > ~/alphachess/auto_shutdown.sh <<'EOF'
#!/bin/bash
# 训练完成后自动关机
echo "训练完成，10 分钟后自动关机..."
sleep 600  # 等待 10 分钟
sudo shutdown -h now
EOF
  
  chmod +x ~/alphachess/auto_shutdown.sh
  echo "✅ 自动关机脚本已创建: ~/alphachess/auto_shutdown.sh"
  echo "   使用方法: ./train_on_azure_vm.sh && ./auto_shutdown.sh"
fi

# ===========================
# 11. 创建训练快捷脚本
# ===========================
echo ""
echo "🚀 步骤 11: 创建训练快捷脚本..."

cat > ~/train.sh <<'EOF'
#!/bin/bash
cd ~/alphachess
./train_on_azure_vm.sh
EOF

chmod +x ~/train.sh

echo "✅ 快捷脚本已创建: ~/train.sh"

# ===========================
# 12. 测试环境
# ===========================
echo ""
echo "🧪 步骤 12: 测试环境..."

echo "Python 版本:"
python3 --version

echo ""
echo "PyTorch 版本:"
python3 -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

echo ""
echo "CUDA 设备:"
python3 -c "import torch; print(f'CUDA devices: {torch.cuda.device_count()}'); [print(f'  {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())]" 2>/dev/null || echo "No CUDA devices"

# ===========================
# 完成
# ===========================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Azure GPU VM 环境配置完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 下一步："
echo "  1. 运行训练: ~/train.sh"
echo "  2. 或手动执行:"
echo "     cd ~/alphachess"
echo "     ./train_on_azure_vm.sh"
echo ""
echo "💡 提示："
echo "  • 使用 tmux 运行长时间任务，避免 SSH 断开"
echo "  • 训练完成后记得停止 VM 以节省成本"
echo "  • 查看 GPU 使用: nvidia-smi"
echo "  • 查看进程: htop"
echo ""
echo "🎯 快捷命令："
echo "  启动训练: ~/train.sh"
echo "  查看日志: tail -f ~/alphachess/logs/*.log"
echo "  停止 VM: sudo shutdown -h now"
echo ""


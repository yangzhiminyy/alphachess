# Azure 部署指南 - AlphaChess 中国象棋 AI

## 📋 方案概述

基于您的需求（人机对战 + 神经网络训练）和每月 $150 预算，以下是推荐的 Azure 部署架构：

### 🎯 推荐架构（分离式部署）

```
┌─────────────────────────────────────────────────────────┐
│                    Azure 部署架构                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1️⃣ Web 应用层（人机对战）                               │
│     └─ Azure App Service (B1 Basic)                     │
│        • FastAPI 后端 + React 前端                       │
│        • CPU 推理（对战响应）                             │
│        • 成本：~$13/月                                    │
│                                                          │
│  2️⃣ 训练层（神经网络训练）                               │
│     └─ Azure VM + GPU (NC6_Promo 或按需启动)            │
│        • PyTorch 训练环境                                │
│        • 按需启动/停止                                    │
│        • 成本：~$0.90/小时（仅训练时运行）                │
│                                                          │
│  3️⃣ 存储层                                               │
│     └─ Azure Blob Storage                               │
│        • 模型文件存储                                     │
│        • 自对弈数据存储                                   │
│        • 成本：~$1-2/月                                   │
│                                                          │
│  4️⃣ 数据库（可选）                                       │
│     └─ Azure Database for PostgreSQL (Flexible)         │
│        • 训练记录、ELO 评分                               │
│        • 成本：~$7/月（Burstable B1ms）                  │
│                                                          │
│  💰 总成本估算：$20-50/月（常驻）+ 训练成本（按需）        │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 方案一：经济型部署（推荐 - 预算友好）

### 架构组件

#### 1. **Azure App Service (B1 Basic) - 人机对战服务**
- **用途**：运行 FastAPI + React Web 界面
- **配置**：
  - 1 Core, 1.75 GB RAM
  - Linux 容器
  - Python 3.10
- **成本**：~$13/月
- **适合场景**：
  - 人机对战（使用 CPU 推理）
  - MCTS 搜索（200 sims，响应时间 15-30 秒可接受）
  - Alpha-Beta 搜索引擎

#### 2. **Azure VM with GPU (NC6_Promo) - 训练专用**
- **用途**：神经网络训练（按需启动）
- **配置**：
  - 6 vCPUs, 56 GB RAM
  - 1x NVIDIA Tesla K80 GPU
- **成本**：~$0.90/小时（仅训练时启动）
- **使用策略**：
  - 每周训练 1-2 次，每次 4-8 小时
  - 月成本：$7-15（取决于训练频率）
  - 训练完成后立即停止 VM

#### 3. **Azure Blob Storage - 模型和数据存储**
- **用途**：
  - 存储训练好的模型（.pt 文件）
  - 自对弈数据（.jsonl 文件）
- **成本**：~$1-2/月（LRS - 本地冗余存储）
- **容量**：50GB 足够

#### 4. **Azure Container Registry (可选)**
- **用途**：存储 Docker 镜像
- **成本**：Basic tier $5/月

### 💰 月度成本估算

| 服务 | 配置 | 月成本（USD） |
|------|------|--------------|
| App Service (B1) | 人机对战服务 | $13 |
| Blob Storage | 模型/数据存储 | $2 |
| VM GPU 训练 | 每周 8 小时 | $7-15 |
| **总计** | | **$22-30/月** |

**剩余预算**：$120-128/月可用于额外的训练或扩容

---

## 🚀 方案二：高性能部署（预算充裕）

如果需要更快的响应速度和更频繁的训练：

#### 1. **Azure App Service (P1V2) - 更强性能**
- 2 Cores, 3.5 GB RAM
- 成本：~$73/月
- 优势：更快的 MCTS 推理

#### 2. **Azure ML Compute Instance - 专业训练**
- GPU 计算实例（NC6s_v3）
- NVIDIA V100 GPU
- 成本：~$3.06/小时
- 按需启动/停止

#### 3. **Azure Cosmos DB - 高性能数据库**
- 用于存储对战记录、ELO 评分
- 成本：~$24/月（400 RU/s）

### 💰 月度成本估算

| 服务 | 月成本（USD） |
|------|--------------|
| App Service (P1V2) | $73 |
| Azure ML Compute (每周 8 小时) | $25-50 |
| Blob Storage | $2 |
| Cosmos DB | $24 |
| **总计** | **$124-149/月** |

---

## 📝 详细部署步骤

### 阶段一：准备工作

#### 1. 创建 Azure 资源组
```bash
az login
az group create --name alphachess-rg --location eastus
```

#### 2. 创建存储账户
```bash
az storage account create \
  --name alphachessstorage \
  --resource-group alphachess-rg \
  --location eastus \
  --sku Standard_LRS

# 创建 Blob 容器
az storage container create \
  --name models \
  --account-name alphachessstorage

az storage container create \
  --name data \
  --account-name alphachessstorage
```

---

### 阶段二：部署 Web 应用（人机对战）

#### 方式 A：使用 Azure App Service（推荐）

1. **创建 App Service Plan**
```bash
az appservice plan create \
  --name alphachess-plan \
  --resource-group alphachess-rg \
  --location eastus \
  --sku B1 \
  --is-linux
```

2. **创建 Web App**
```bash
az webapp create \
  --name alphachess-web \
  --resource-group alphachess-rg \
  --plan alphachess-plan \
  --runtime "PYTHON:3.10"
```

3. **配置部署**
```bash
# 从 GitHub/本地部署
az webapp deployment source config-local-git \
  --name alphachess-web \
  --resource-group alphachess-rg

# 获取部署 URL
az webapp deployment list-publishing-credentials \
  --name alphachess-web \
  --resource-group alphachess-rg \
  --query scmUri \
  --output tsv
```

4. **配置环境变量**
```bash
az webapp config appsettings set \
  --name alphachess-web \
  --resource-group alphachess-rg \
  --settings \
    AZURE_STORAGE_ACCOUNT="alphachessstorage" \
    AZURE_STORAGE_KEY="<your-storage-key>" \
    MODEL_PATH="/home/models/latest.pt"
```

5. **部署代码**
```bash
# 在项目根目录
git remote add azure <deployment-url>
git push azure main
```

#### 方式 B：使用 Docker 容器（更灵活）

1. **创建 Dockerfile**（见下方配置文件部分）

2. **构建并推送镜像**
```bash
# 创建 Container Registry
az acr create \
  --name alphachessacr \
  --resource-group alphachess-rg \
  --sku Basic

# 登录
az acr login --name alphachessacr

# 构建镜像
docker build -t alphachessacr.azurecr.io/alphachess:latest .

# 推送
docker push alphachessacr.azurecr.io/alphachess:latest
```

3. **从容器部署 Web App**
```bash
az webapp create \
  --name alphachess-web \
  --resource-group alphachess-rg \
  --plan alphachess-plan \
  --deployment-container-image-name alphachessacr.azurecr.io/alphachess:latest
```

---

### 阶段三：设置 GPU 训练环境

#### 选项 A：Azure VM with GPU（经济型）

1. **创建 GPU 虚拟机**
```bash
az vm create \
  --name alphachess-train-vm \
  --resource-group alphachess-rg \
  --location eastus \
  --size Standard_NC6_Promo \
  --image microsoft-dsvm:ubuntu-2004:2004-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys
```

2. **连接 VM 并配置环境**
```bash
# SSH 连接
ssh azureuser@<vm-public-ip>

# 安装依赖
sudo apt update
sudo apt install -y python3-pip git
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip3 install fastapi uvicorn numpy

# 克隆代码
git clone <your-repo-url>
cd alphachess

# 挂载 Blob Storage（可选）
sudo apt install -y blobfuse
```

3. **运行训练**
```bash
# 生成自对弈数据
python scripts/self_play_generic.py \
  --game xiangqi \
  --games 100 \
  --sims 400 \
  --out /data/selfplay_001.jsonl

# 训练模型
python scripts/train_generic.py \
  --game xiangqi \
  --data /data/selfplay_001.jsonl \
  --model_out /models/v1.pt \
  --epochs 20 \
  --batch_size 128 \
  --lr 0.001

# 上传到 Blob Storage
az storage blob upload \
  --account-name alphachessstorage \
  --container-name models \
  --name v1.pt \
  --file /models/v1.pt
```

4. **停止 VM 以节省成本**
```bash
az vm deallocate \
  --name alphachess-train-vm \
  --resource-group alphachess-rg
```

#### 选项 B：Azure Machine Learning（专业级）

1. **创建 ML 工作区**
```bash
az ml workspace create \
  --name alphachess-ml \
  --resource-group alphachess-rg \
  --location eastus
```

2. **创建计算实例**（通过 Azure Portal 更方便）
- 登录 Azure Portal
- 进入 Azure Machine Learning Studio
- 创建计算实例（NC6s_v3 with GPU）
- 配置自动关闭（训练完成后自动停止）

3. **提交训练作业**
```python
# training_job.py
from azure.ai.ml import MLClient
from azure.ai.ml.entities import command

ml_client = MLClient.from_config()

job = command(
    code="./scripts",
    command="python train_generic.py --game xiangqi --data ${{inputs.data}} --epochs 20",
    environment="AzureML-pytorch-1.13-ubuntu20.04-py38-cuda11.7-gpu",
    compute="gpu-cluster",
    inputs={"data": {"type": "uri_folder", "path": "azureml://datastores/data"}},
)

ml_client.jobs.create_or_update(job)
```

---

### 阶段四：集成存储和自动化

#### 1. 修改代码以使用 Azure Blob Storage

创建 `azure_storage.py`（见下方配置文件部分）

#### 2. 配置自动训练流水线

创建 Azure Function 或 Logic App 实现：
- 每周自动启动训练 VM
- 运行自对弈 + 训练
- 上传模型到 Blob Storage
- 停止 VM
- 通知管理员

---

## 🛠️ 必要的配置文件

### 1. Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. .dockerignore
```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
data/
models/*.pt
.git/
.gitignore
*.log
.vscode/
.cursor/
```

### 3. startup.sh（Azure App Service）
```bash
#!/bin/bash
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

---

## 📊 成本优化建议

### 1. **使用 Azure Reserved Instances**
- 如果确定长期使用，购买 1 年预留实例可节省 30-40%

### 2. **合理使用 GPU 资源**
- 训练时使用 Spot VM（可节省 60-90%，但可能被抢占）
- 设置自动关闭策略
- 批量训练（一次性完成多轮迭代）

```bash
# 使用 Spot VM 创建训练实例
az vm create \
  --name alphachess-train-spot \
  --resource-group alphachess-rg \
  --size Standard_NC6 \
  --priority Spot \
  --max-price 0.50 \
  --eviction-policy Deallocate
```

### 3. **使用 Azure 学生订阅（如适用）**
- 每月 $100 免费额度
- 免费的 B1 App Service（12 个月）

### 4. **CDN 加速（可选）**
- 使用 Azure CDN 加速前端静态资源
- 成本很低（$0.081/GB）

### 5. **监控和自动化**
- 设置 Azure Monitor 警报（成本超限时通知）
- 使用 Azure Automation 自动启动/停止 VM

```bash
# 创建预算警报
az consumption budget create \
  --budget-name alphachess-budget \
  --amount 150 \
  --time-grain Monthly \
  --category Cost
```

---

## 🔒 安全建议

### 1. **使用 Azure Key Vault 存储敏感信息**
```bash
az keyvault create \
  --name alphachess-kv \
  --resource-group alphachess-rg \
  --location eastus

# 存储存储密钥
az keyvault secret set \
  --vault-name alphachess-kv \
  --name storage-key \
  --value "<your-storage-key>"
```

### 2. **启用 HTTPS**
- App Service 自动提供 SSL/TLS
- 可绑定自定义域名 + Let's Encrypt 证书

### 3. **配置网络安全组（NSG）**
- 限制 VM 的入站访问
- 只允许必要的端口（SSH 22, HTTP 80, HTTPS 443）

---

## 📈 监控和维护

### 1. **Azure Application Insights**
```bash
az monitor app-insights component create \
  --app alphachess-insights \
  --resource-group alphachess-rg \
  --location eastus \
  --application-type web
```

在 `api/server.py` 中集成：
```python
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=<your-key>'
))
```

### 2. **设置日志分析**
- 监控 API 响应时间
- 跟踪错误率
- 分析用户行为

---

## 🚦 推荐的实施路线图

### 第 1 周：基础部署
- ✅ 创建 Azure 资源组和存储账户
- ✅ 部署 Web 应用到 App Service
- ✅ 测试人机对战功能

### 第 2 周：训练环境
- ✅ 创建 GPU 虚拟机
- ✅ 运行初始训练（小规模）
- ✅ 集成 Blob Storage

### 第 3 周：优化和自动化
- ✅ 设置自动启停脚本
- ✅ 配置监控和警报
- ✅ 性能优化

### 第 4 周：增强功能
- ✅ 添加用户认证（Azure AD）
- ✅ 实现对战历史记录
- ✅ 部署多个模型版本

---

## 🎯 最终推荐配置（$150 预算）

```
┌─────────────────────────────────────────┐
│  生产环境配置                            │
├─────────────────────────────────────────┤
│  • App Service B1: $13/月               │
│  • Blob Storage: $2/月                  │
│  • GPU VM (按需): $10-20/月             │
│  • Application Insights: $5/月          │
│  • 预留预算: $110-120/月                │
│                                         │
│  总计: $30-40/月（基础运营）            │
│        + $110 训练/扩容预算              │
└─────────────────────────────────────────┘
```

这个配置可以：
- ✅ 稳定运行人机对战服务
- ✅ 每周进行 8-16 小时 GPU 训练
- ✅ 支持 100+ 并发用户
- ✅ 自动扩展能力
- ✅ 充足的预算余量

---

## ❓ 常见问题

### Q1: 能否完全使用免费层？
A: 可以使用 Azure 免费层进行概念验证，但不适合生产：
- F1 Free App Service（非常慢，无自定义域名）
- 免费 Blob Storage（5GB 限制）
- 无 GPU 免费选项

### Q2: 训练速度多快？
A: 
- NC6 (K80): ~5-10 分钟/epoch（10k 样本）
- NC6s_v3 (V100): ~2-3 分钟/epoch

### Q3: 如何处理并发用户？
A: 
- B1 可处理 10-20 并发用户
- 升级到 P1V2 可处理 100+ 用户
- 使用 Azure Front Door + 多实例扩展

### Q4: 模型更新如何自动化？
A: 使用 Azure DevOps Pipeline 或 GitHub Actions：
```yaml
# .github/workflows/deploy.yml
name: Deploy Model
on:
  push:
    paths:
      - 'models/*.pt'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Upload to Blob
        run: |
          az storage blob upload \
            --account-name alphachessstorage \
            --container-name models \
            --name latest.pt \
            --file models/latest.pt
```

---

## 📞 获取帮助

- Azure 文档：https://docs.microsoft.com/azure
- PyTorch on Azure：https://docs.microsoft.com/azure/machine-learning/how-to-train-pytorch
- Azure 定价计算器：https://azure.microsoft.com/pricing/calculator/

---

**祝您部署顺利！如有问题，欢迎随时咨询。** 🚀


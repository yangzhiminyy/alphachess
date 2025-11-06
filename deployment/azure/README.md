# Azure 部署文档和脚本

本目录包含 AlphaChess 项目部署到 Azure 云平台所需的所有文档、脚本和配置文件。

---

## 📁 目录结构

```
deployment/azure/
├── README.md                    # 本文件
├── Dockerfile                   # Docker 容器配置
├── .dockerignore               # Docker 构建排除规则
├── requirements-azure.txt      # Azure 集成额外依赖
│
├── docs/                       # 📚 Documentation
│   ├── AZURE_QUICKSTART.md          # ⭐ Quick Start Guide (Recommended)
│   ├── azure_deployment_guide.md    # Complete Deployment Guide (45+ pages)
│   ├── deployment_checklist.md      # Deployment Checklist
│   ├── architecture_diagram.txt     # Architecture Diagram & Cost Analysis
│   └── file_organization_guide.md   # File Organization Guide
│
├── scripts/                    # 🔧 自动化脚本目录
│   ├── deploy_to_azure.sh          # ⭐ 一键部署 Web 应用脚本
│   ├── setup_azure_vm.sh           # GPU VM 环境配置脚本
│   └── train_on_azure_vm.sh        # 训练执行脚本
│
└── helpers/                    # 🛠️ 工具代码目录
    └── azure_storage_helper.py     # Azure Blob Storage 辅助类
```

---

## 🚀 快速开始

### 1. 首次部署（10 分钟）

```bash
# 1. 登录 Azure
az login

# 2. 一键部署 Web 应用
cd deployment/azure/scripts
bash deploy_to_azure.sh
```

**完成后访问**: `https://YOUR_APP_NAME.azurewebsites.net/web/`

### 2. 配置训练环境（30 分钟 - 仅首次）

```bash
# 1. 创建 GPU 虚拟机
az vm create \
  --name alphachess-train \
  --resource-group alphachess-rg \
  --size Standard_NC6_Promo \
  --image microsoft-dsvm:ubuntu-2004:2004-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys

# 2. 上传配置脚本
scp setup_azure_vm.sh train_on_azure_vm.sh azureuser@<VM_IP>:~

# 3. SSH 到 VM 并配置
ssh azureuser@<VM_IP>
bash setup_azure_vm.sh
```

### 3. 训练 AI（每周运行）

```bash
# 在 GPU VM 上运行
ssh azureuser@<VM_IP>
cd ~/alphachess
tmux new -s training
bash train_on_azure_vm.sh

# 训练完成后停止 VM（重要！）
az vm deallocate --name alphachess-train --resource-group alphachess-rg
```

---

## 📖 文档阅读顺序

### 🌟 推荐路线（循序渐进）

1. **今天 (15 分钟)**
   - `docs/AZURE_QUICKSTART.md` - 了解整体方案和快速部署
   - `docs/architecture_diagram.txt` - 查看架构和成本分析

2. **明天 (1-2 小时)**
   - `docs/deployment_checklist.md` - 跟随检查清单执行部署
   - 运行 `scripts/deploy_to_azure.sh` - 部署 Web 应用

3. **本周 (2-3 小时)**
   - `docs/azure_deployment_guide.md` - 深入学习完整部署方案
   - 配置 GPU 训练环境
   - 完成首次训练

---

## 💰 成本说明

### 推荐配置（$150 预算内）

```
固定成本（24/7 运行）:
├─ Azure App Service (B1)    : $13/月
├─ Blob Storage              : $2/月
├─ Container Registry        : $5/月
└─ 小计                      : $20/月

训练成本（按需启动）:
├─ GPU VM (NC6_Promo)        : $0.90/小时
├─ 每周训练 8 小时            : $7.20/周
└─ 月成本                     : $28.80/月

总计: $48.80/月
剩余预算: $101.20/月 ✨
```

---

## 🔧 核心脚本说明

### 1. deploy_to_azure.sh
**用途**: 自动部署 Web 应用到 Azure

**功能**:
- 创建所有必要的 Azure 资源
- 构建并推送 Docker 镜像
- 配置环境变量
- 部署 Web 应用

**运行时间**: 10-15 分钟

**使用方法**:
```bash
cd deployment/azure/scripts
bash deploy_to_azure.sh
```

### 2. setup_azure_vm.sh
**用途**: 配置 GPU 虚拟机训练环境

**功能**:
- 安装系统依赖和 Python
- 配置 CUDA 和 PyTorch
- 设置 Azure CLI
- 配置存储连接

**运行时间**: 20-30 分钟（仅首次）

**使用方法**:
```bash
ssh azureuser@<VM_IP>
bash setup_azure_vm.sh
```

### 3. train_on_azure_vm.sh
**用途**: 执行完整训练流程

**功能**:
- 从 Blob Storage 下载当前模型
- 生成自对弈数据（100 局）
- 训练神经网络（20 epochs）
- 上传新模型到 Blob Storage

**运行时间**: 6-10 小时

**使用方法**:
```bash
ssh azureuser@<VM_IP>
cd ~/alphachess
tmux new -s training
bash train_on_azure_vm.sh
```

---

## 🛠️ 辅助工具

### azure_storage_helper.py

Azure Blob Storage 操作辅助类，提供：

- 上传/下载模型文件
- 列出存储中的文件
- 自动缓存管理

**使用示例**:
```python
from deployment.azure.helpers.azure_storage_helper import AzureBlobHelper

# 初始化
blob = AzureBlobHelper()

# 上传模型
blob.upload_file("models/latest.pt", "models", "latest.pt")

# 下载模型
blob.download_file("models", "latest.pt", "/tmp/latest.pt")

# 获取模型路径（自动下载并缓存）
model_path = blob.get_model_path("latest.pt")
```

---

## 📋 部署前检查

在开始部署前，请确保：

- [ ] 已安装 Azure CLI (`az --version`)
- [ ] 已安装 Docker Desktop (`docker --version`)
- [ ] 已登录 Azure (`az login`)
- [ ] 已验证订阅额度
- [ ] 已阅读快速开始指南

---

## 🎯 常见任务速查

### 启动训练
```bash
az vm start --name alphachess-train --resource-group alphachess-rg
ssh azureuser@<VM_IP>
cd ~/alphachess && tmux new -s training
bash train_on_azure_vm.sh
```

### 停止 VM（节省成本）
```bash
az vm deallocate --name alphachess-train --resource-group alphachess-rg
```

### 查看 Web 应用日志
```bash
az webapp log tail --name YOUR_APP_NAME --resource-group alphachess-rg
```

### 上传新模型
```bash
az storage blob upload \
  --account-name YOUR_STORAGE_ACCOUNT \
  --container-name models \
  --name latest.pt \
  --file ./models/latest.pt \
  --overwrite
```

### 重启 Web 应用
```bash
az webapp restart --name YOUR_APP_NAME --resource-group alphachess-rg
```

---

## ❓ 故障排除

### Web 应用无法访问
1. 检查部署状态: `az webapp show --name YOUR_APP_NAME`
2. 查看日志: `az webapp log tail --name YOUR_APP_NAME`
3. 重启应用: `az webapp restart --name YOUR_APP_NAME`

### GPU 训练失败
1. 检查 CUDA: `nvidia-smi`
2. 验证 PyTorch: `python3 -c "import torch; print(torch.cuda.is_available())"`
3. 查看训练日志: `tail -f ~/alphachess/logs/*.log`

### 成本超出预算
1. 检查 VM 状态: `az vm list --query "[].{Name:name, PowerState:powerState}"`
2. 停止未使用的资源
3. 考虑使用 Spot VM

---

## 📞 获取帮助

- **快速问题**: 查看 `docs/AZURE_QUICKSTART.md`
- **详细指南**: 查看 `docs/azure_deployment_guide.md`
- **检查清单**: 查看 `docs/deployment_checklist.md`
- **Azure 文档**: https://docs.microsoft.com/azure
- **项目主文档**: 返回 `../../README.md`

---

## 🎊 开始部署

准备好了吗？按照以下步骤开始：

1. 阅读 `docs/AZURE_QUICKSTART.md`
2. 运行 `scripts/deploy_to_azure.sh`
3. 访问您的 AlphaChess Web 应用！

**祝您部署顺利！** 🚀

---

**相关链接**:
- [项目主 README](../../README.md)
- [AlphaZero 框架文档](../../docs/README_FRAMEWORK.md)
- [训练指南](../../docs/MIGRATION_GUIDE.md)


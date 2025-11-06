# Azure 快速部署指南 ⚡

> **适用于每月 $150 预算的 AlphaChess 部署方案**

---

## 🎯 一键部署（推荐）

如果您想快速部署到 Azure，只需 3 个命令：

```bash
# 1. 确保已安装 Azure CLI 和 Docker
az --version
docker --version

# 2. 登录 Azure
az login

# 3. 运行自动部署脚本
./deploy_to_azure.sh
```

**完成！** 🎉 您的 AlphaChess 应用将在 5-10 分钟内部署完成。

---

## 📋 部署后的资源

部署脚本将自动创建以下 Azure 资源：

| 资源 | 用途 | 月成本 |
|------|------|--------|
| **App Service (B1)** | Web 应用 + API | ~$13 |
| **Blob Storage** | 模型和数据存储 | ~$2 |
| **Container Registry** | Docker 镜像 | ~$5 |
| **总计** | | **~$20/月** |

**剩余预算**: ~$130/月，可用于 GPU 训练（按需使用）

---

## 🎮 人机对战

部署完成后，访问：

```
https://YOUR_APP_NAME.azurewebsites.net/web/
```

您可以立即开始与 AI 对战！

---

## 🧠 训练神经网络

### 方案 A：一键训练（推荐）

使用我们的自动化训练脚本：

1. **创建 GPU 虚拟机**（仅需创建一次）：

```bash
az vm create \
  --name alphachess-train \
  --resource-group alphachess-rg \
  --size Standard_NC6_Promo \
  --image microsoft-dsvm:ubuntu-2004:2004-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys
```

**成本**: ~$0.90/小时（仅训练时运行）

2. **SSH 连接到 VM**：

```bash
ssh azureuser@<VM_IP_ADDRESS>
```

3. **配置环境**（仅首次需要）：

```bash
# 上传配置脚本到 VM
scp setup_azure_vm.sh azureuser@<VM_IP>:~
scp train_on_azure_vm.sh azureuser@<VM_IP>:~

# SSH 到 VM 并运行配置
ssh azureuser@<VM_IP>
chmod +x setup_azure_vm.sh
./setup_azure_vm.sh
```

4. **开始训练**：

```bash
# 在 VM 上运行
cd ~/alphachess
./train_on_azure_vm.sh
```

5. **训练完成后停止 VM**（重要！节省成本）：

```bash
# 在本地运行
az vm deallocate --name alphachess-train --resource-group alphachess-rg
```

### 方案 B：使用 Azure Machine Learning（高级）

如果需要更专业的训练管理，可以使用 Azure ML：

- 自动启停
- 实验跟踪
- 模型版本管理
- 分布式训练

详见 `azure_deployment_guide.md` 的完整说明。

---

## 💰 成本监控

### 查看当前支出

```bash
az consumption usage list \
  --start-date $(date -d "1 month ago" +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[].{Service:instanceName,Cost:pretaxCost}" \
  --output table
```

### 设置预算警报

```bash
az consumption budget create \
  --budget-name alphachess-budget \
  --amount 150 \
  --time-grain Monthly \
  --category Cost
```

---

## 🔄 训练工作流程

推荐的训练周期（充分利用 $150 预算）：

```
┌──────────────────────────────────────────────────────┐
│  周一至周五: Web 应用运行（人机对战）                  │
│  成本: ~$0.43/天 × 7 = $3/周                          │
│                                                      │
│  周末: 启动 GPU VM 进行训练                           │
│  • 自对弈生成数据: 2-4 小时                          │
│  • 训练神经网络: 4-8 小时                            │
│  • 成本: $0.90/小时 × 8小时 = $7.20/次               │
│                                                      │
│  月度成本估算:                                        │
│  • Web 应用: $13                                      │
│  • 存储: $2                                           │
│  • Container Registry: $5                            │
│  • GPU 训练 (每周一次): $7 × 4 = $28                 │
│  • 总计: ~$48/月                                      │
│                                                      │
│  剩余预算: $102/月 可用于额外训练或扩容               │
└──────────────────────────────────────────────────────┘
```

---

## 📊 监控和管理

### 查看 Web 应用日志

```bash
az webapp log tail \
  --name YOUR_APP_NAME \
  --resource-group alphachess-rg
```

### 查看 GPU 使用情况（在 VM 上）

```bash
watch -n 1 nvidia-smi
```

### 下载最新模型

```bash
az storage blob download \
  --account-name YOUR_STORAGE_ACCOUNT \
  --container-name models \
  --name latest.pt \
  --file ./latest.pt
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

---

## 🛠️ 常用命令速查

### Web 应用管理

```bash
# 重启 Web 应用
az webapp restart --name YOUR_APP_NAME --resource-group alphachess-rg

# 查看应用状态
az webapp show --name YOUR_APP_NAME --resource-group alphachess-rg --query state

# 更新应用设置
az webapp config appsettings set \
  --name YOUR_APP_NAME \
  --resource-group alphachess-rg \
  --settings KEY=VALUE
```

### GPU VM 管理

```bash
# 启动 VM
az vm start --name alphachess-train --resource-group alphachess-rg

# 停止 VM（计费停止）
az vm deallocate --name alphachess-train --resource-group alphachess-rg

# 查看 VM 状态
az vm show --name alphachess-train --resource-group alphachess-rg --query powerState

# 删除 VM（如果不再需要）
az vm delete --name alphachess-train --resource-group alphachess-rg --yes
```

### 存储管理

```bash
# 列出所有模型
az storage blob list \
  --account-name YOUR_STORAGE_ACCOUNT \
  --container-name models \
  --output table

# 列出所有数据文件
az storage blob list \
  --account-name YOUR_STORAGE_ACCOUNT \
  --container-name data \
  --output table
```

---

## 🔐 安全建议

1. **不要将密钥提交到 Git**
   - 使用 Azure Key Vault 存储敏感信息
   - 配置文件 `azure_config.env` 已被 `.gitignore` 忽略

2. **限制 VM 访问**
   - 只允许您的 IP 访问 SSH（端口 22）
   - 使用 SSH 密钥而非密码

3. **启用 HTTPS**
   - App Service 自动提供 SSL/TLS
   - 可绑定自定义域名

4. **定期备份**
   - 模型文件自动存储在 Blob Storage（冗余）
   - 设置自动快照策略

---

## 🐛 故障排除

### 问题：Web 应用无法启动

```bash
# 查看详细日志
az webapp log tail --name YOUR_APP_NAME --resource-group alphachess-rg

# 检查 Docker 容器状态
az webapp config container show --name YOUR_APP_NAME --resource-group alphachess-rg
```

### 问题：GPU 训练失败

```bash
# 检查 CUDA 是否可用
python3 -c "import torch; print(torch.cuda.is_available())"

# 查看 GPU 状态
nvidia-smi
```

### 问题：成本超出预算

```bash
# 查看详细账单
az consumption usage list --output table

# 停止所有非必要资源
az vm deallocate --name alphachess-train --resource-group alphachess-rg
```

---

## 📚 更多资源

- **完整部署指南**: `azure_deployment_guide.md`
- **Azure 文档**: https://docs.microsoft.com/azure
- **PyTorch on Azure**: https://docs.microsoft.com/azure/machine-learning/how-to-train-pytorch
- **成本计算器**: https://azure.microsoft.com/pricing/calculator/

---

## ✨ 优化建议

### 1. 使用 Spot VM 节省成本（高级）

Spot VM 可节省 60-90% 成本，但可能被抢占：

```bash
az vm create \
  --name alphachess-train-spot \
  --resource-group alphachess-rg \
  --size Standard_NC6 \
  --priority Spot \
  --max-price 0.50 \
  --eviction-policy Deallocate
```

### 2. 启用自动扩展（高流量）

如果用户增多，可以配置自动扩展：

```bash
az monitor autoscale create \
  --resource-group alphachess-rg \
  --resource YOUR_APP_NAME \
  --resource-type Microsoft.Web/serverfarms \
  --min-count 1 \
  --max-count 3 \
  --count 1
```

### 3. 使用 CDN 加速（全球用户）

如果有海外用户，可以启用 Azure CDN：

```bash
az cdn profile create \
  --name alphachess-cdn \
  --resource-group alphachess-rg \
  --sku Standard_Microsoft
```

---

## 🎓 学习路径

如果您是 Azure 新手，推荐按以下顺序学习：

1. ✅ **第 1 天**: 完成基础 Web 应用部署
2. ✅ **第 2-3 天**: 熟悉 Azure Portal 和命令行工具
3. ✅ **第 4-5 天**: 配置 GPU VM 并运行首次训练
4. ✅ **第 2 周**: 优化训练流程和成本管理
5. ✅ **第 3-4 周**: 探索高级功能（CI/CD, 监控, 自动化）

---

## 🆘 获取帮助

遇到问题？

1. 查看日志输出
2. 参考 `azure_deployment_guide.md` 完整文档
3. 访问 Azure 文档和社区论坛
4. 检查 Azure 服务健康状态

---

**祝您部署顺利！开始训练您的 AlphaChess AI 吧！** 🚀🎮


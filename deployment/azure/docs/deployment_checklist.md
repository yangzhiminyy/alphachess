# ✅ AlphaChess Azure 部署检查清单

使用此清单确保每个步骤都正确完成。

---

## 📋 阶段 1: 准备工作

### 本地环境设置

- [ ] **安装 Azure CLI**
  ```powershell
  winget install Microsoft.AzureCLI
  # 验证: az --version
  ```

- [ ] **安装 Docker Desktop**
  ```powershell
  winget install Docker.DockerDesktop
  # 验证: docker --version
  ```

- [ ] **安装 Git Bash 或 WSL**
  ```powershell
  # 选项 1: Git Bash (推荐)
  winget install Git.Git
  
  # 选项 2: WSL
  wsl --install
  ```

- [ ] **登录 Azure**
  ```bash
  az login
  # 确保登录成功并选择正确的订阅
  ```

- [ ] **验证订阅额度**
  ```bash
  az account show --query "{Name:name, ID:id, State:state}"
  # 确认有 $150 可用额度
  ```

---

## 📋 阶段 2: Web 应用部署

### 运行部署脚本

- [ ] **检查项目文件**
  ```bash
  ls -la
  # 确认存在: deploy_to_azure.sh, Dockerfile, requirements.txt
  ```

- [ ] **运行部署脚本**
  ```bash
  bash deploy_to_azure.sh
  ```

- [ ] **等待部署完成** (预计 10-15 分钟)
  - [ ] 资源组创建成功
  - [ ] 存储账户创建成功
  - [ ] Container Registry 创建成功
  - [ ] Docker 镜像构建并推送成功
  - [ ] App Service 创建成功
  - [ ] 环境变量配置成功

- [ ] **记录重要信息**（脚本会自动保存到 `azure_config.env`）
  ```
  资源组名称: _________________
  Web App 名称: _________________
  存储账户: _________________
  访问 URL: https://_________________.azurewebsites.net
  ```

### 验证部署

- [ ] **访问 Web 应用**
  ```
  打开浏览器访问: https://YOUR_APP_NAME.azurewebsites.net/web/
  ```

- [ ] **测试 API 健康检查**
  ```bash
  curl https://YOUR_APP_NAME.azurewebsites.net/api/health
  # 应返回: {"status":"ok"}
  ```

- [ ] **测试人机对战功能**
  - [ ] 能看到棋盘界面
  - [ ] 能创建新游戏
  - [ ] 能移动棋子
  - [ ] AI 能响应（可能较慢，15-30 秒）

- [ ] **检查应用日志**
  ```bash
  az webapp log tail \
    --name YOUR_APP_NAME \
    --resource-group alphachess-rg
  # 确认没有错误
  ```

---

## 📋 阶段 3: GPU 训练环境（可选但推荐）

### 创建 GPU 虚拟机

- [ ] **创建 VM**
  ```bash
  az vm create \
    --name alphachess-train \
    --resource-group alphachess-rg \
    --size Standard_NC6_Promo \
    --image microsoft-dsvm:ubuntu-2004:2004-gen2:latest \
    --admin-username azureuser \
    --generate-ssh-keys
  ```

- [ ] **记录 VM IP 地址**
  ```bash
  az vm show \
    --name alphachess-train \
    --resource-group alphachess-rg \
    --show-details \
    --query publicIps \
    --output tsv
  
  VM IP: _________________
  ```

- [ ] **测试 SSH 连接**
  ```bash
  ssh azureuser@<VM_IP>
  # 应该能成功连接
  ```

### 配置训练环境

- [ ] **上传配置脚本**
  ```bash
  scp setup_azure_vm.sh azureuser@<VM_IP>:~
  scp train_on_azure_vm.sh azureuser@<VM_IP>:~
  ```

- [ ] **上传项目代码**
  ```bash
  # 选项 1: 使用 Git
  ssh azureuser@<VM_IP>
  git clone <YOUR_GIT_REPO>
  
  # 选项 2: 使用 SCP
  scp -r alphachess azureuser@<VM_IP>:~/
  ```

- [ ] **运行环境配置脚本**
  ```bash
  ssh azureuser@<VM_IP>
  chmod +x setup_azure_vm.sh
  bash setup_azure_vm.sh
  ```

- [ ] **验证环境配置**
  - [ ] Python 3.10 已安装
  - [ ] PyTorch 已安装
  - [ ] CUDA 可用
  - [ ] Azure CLI 已登录
  - [ ] 存储账户已配置

- [ ] **测试 GPU**
  ```bash
  nvidia-smi
  # 应显示 Tesla K80 GPU 信息
  
  python3 -c "import torch; print(torch.cuda.is_available())"
  # 应返回 True
  ```

---

## 📋 阶段 4: 首次训练

### 准备训练

- [ ] **SSH 连接到 VM**
  ```bash
  ssh azureuser@<VM_IP>
  ```

- [ ] **启动 tmux 会话**（防止 SSH 断开）
  ```bash
  tmux new -s training
  ```

- [ ] **导航到项目目录**
  ```bash
  cd ~/alphachess
  ```

- [ ] **配置 Azure Storage 环境变量**
  ```bash
  export AZURE_STORAGE_ACCOUNT="your_storage_account"
  export AZURE_STORAGE_KEY="your_storage_key"
  ```

### 运行训练

- [ ] **执行训练脚本**
  ```bash
  bash train_on_azure_vm.sh
  ```

- [ ] **监控训练过程**
  - [ ] 自对弈数据生成开始（2-4 小时）
  - [ ] 自对弈数据生成完成
  - [ ] 训练开始（4-6 小时）
  - [ ] 训练完成
  - [ ] 模型上传到 Blob Storage

- [ ] **验证训练结果**
  ```bash
  # 在 VM 上
  ls -lh models/
  ls -lh data/
  
  # 在本地
  az storage blob list \
    --account-name YOUR_STORAGE_ACCOUNT \
    --container-name models \
    --output table
  ```

### 清理资源

- [ ] **退出 tmux**
  ```bash
  # 按 Ctrl+B, 然后按 D (分离会话)
  # 或
  exit  # 如果训练已完成
  ```

- [ ] **停止 GPU VM**（重要！节省成本）
  ```bash
  # 在本地运行
  az vm deallocate \
    --name alphachess-train \
    --resource-group alphachess-rg
  ```

- [ ] **验证 VM 已停止**
  ```bash
  az vm show \
    --name alphachess-train \
    --resource-group alphachess-rg \
    --query powerState
  # 应显示: "VM deallocated"
  ```

---

## 📋 阶段 5: 测试新模型

### 更新 Web 应用模型

- [ ] **验证新模型已上传**
  ```bash
  az storage blob list \
    --account-name YOUR_STORAGE_ACCOUNT \
    --container-name models \
    --query "[?name=='latest.pt']"
  ```

- [ ] **重启 Web 应用**（加载新模型）
  ```bash
  az webapp restart \
    --name YOUR_APP_NAME \
    --resource-group alphachess-rg
  ```

- [ ] **等待应用重启**（1-2 分钟）

- [ ] **测试新模型**
  - [ ] 访问 Web 界面
  - [ ] 创建新游戏
  - [ ] 与 AI 对战
  - [ ] 观察 AI 是否有改进

---

## 📋 阶段 6: 成本监控

### 设置预算警报

- [ ] **创建预算**
  ```bash
  az consumption budget create \
    --budget-name alphachess-budget \
    --amount 150 \
    --time-grain Monthly \
    --category Cost
  ```

- [ ] **查看当前支出**
  ```bash
  az consumption usage list \
    --start-date $(date -d "1 month ago" +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d)
  ```

- [ ] **配置成本警报**（通过 Azure Portal）
  - [ ] 登录 Azure Portal
  - [ ] 转到 Cost Management + Billing
  - [ ] 设置预算警报（50%, 80%, 100%）
  - [ ] 配置邮件通知

### 验证资源状态

- [ ] **检查所有资源**
  ```bash
  az resource list \
    --resource-group alphachess-rg \
    --output table
  ```

- [ ] **确认 GPU VM 已停止**
  ```bash
  az vm list \
    --resource-group alphachess-rg \
    --query "[].{Name:name, PowerState:powerState}" \
    --output table
  # VM 应显示 "VM deallocated"
  ```

- [ ] **记录预计成本**
  ```
  固定成本:
  - App Service: $13/月
  - Blob Storage: $2/月
  - Container Registry: $5/月
  小计: $20/月
  
  训练成本 (本月预计):
  - GPU 训练时间: _____ 小时
  - 成本: _____ × $0.90 = $_____
  
  总计: $_____/月
  ```

---

## 📋 后续维护清单

### 每周任务

- [ ] **启动训练** (周末)
  ```bash
  az vm start --name alphachess-train --resource-group alphachess-rg
  ssh azureuser@<VM_IP>
  cd ~/alphachess && tmux new -s training
  bash train_on_azure_vm.sh
  ```

- [ ] **停止 VM** (训练完成后)
  ```bash
  az vm deallocate --name alphachess-train --resource-group alphachess-rg
  ```

- [ ] **检查成本**
  ```bash
  az consumption usage list --output table
  ```

### 每月任务

- [ ] **审查训练进度**
  - [ ] 查看模型版本历史
  - [ ] 运行 Arena 评测
  - [ ] 记录 ELO 评分变化

- [ ] **备份重要数据**
  - [ ] 下载最佳模型
  - [ ] 保存训练记录

- [ ] **优化成本**
  - [ ] 删除旧的自对弈数据
  - [ ] 删除过时的模型文件
  - [ ] 检查未使用的资源

---

## 🎯 成功标准

当您完成以下所有项目时，部署即为成功：

- [x] ✅ Web 应用可以访问
- [x] ✅ 人机对战功能正常
- [x] ✅ GPU 训练环境已配置
- [x] ✅ 完成至少 1 轮训练
- [x] ✅ 模型能够上传和下载
- [x] ✅ 成本在预算内（< $150/月）
- [x] ✅ 能够独立启动和停止训练
- [x] ✅ 设置了成本警报

---

## 📝 故障排除清单

### Web 应用问题

- [ ] **应用无法访问**
  - [ ] 检查部署状态: `az webapp show --name YOUR_APP_NAME`
  - [ ] 查看日志: `az webapp log tail --name YOUR_APP_NAME`
  - [ ] 重启应用: `az webapp restart --name YOUR_APP_NAME`

- [ ] **AI 响应很慢**
  - [ ] 正常现象（B1 使用 CPU 推理，15-30 秒）
  - [ ] 考虑升级到 P1V2 ($73/月)

### GPU 训练问题

- [ ] **CUDA 不可用**
  ```bash
  # 检查驱动
  nvidia-smi
  
  # 重新安装 CUDA 版本的 PyTorch
  pip3 install torch --index-url https://download.pytorch.org/whl/cu118
  ```

- [ ] **训练中断**
  - [ ] 使用 tmux 避免 SSH 断开
  - [ ] 添加检查点保存和恢复功能

### 成本问题

- [ ] **成本超出预期**
  - [ ] 检查 VM 是否忘记停止
  - [ ] 查看详细账单
  - [ ] 考虑使用 Spot VM

---

## 📞 需要帮助？

如果遇到问题：

1. **查看详细文档**
   - `AZURE_QUICKSTART.md` - 快速开始
   - `azure_deployment_guide.md` - 完整指南
   - `部署总结.md` - 方案总结

2. **检查日志**
   ```bash
   # Web 应用日志
   az webapp log tail --name YOUR_APP_NAME --resource-group alphachess-rg
   
   # VM 日志
   ssh azureuser@<VM_IP>
   tail -f ~/alphachess/logs/*.log
   ```

3. **联系支持**
   - Azure 技术支持
   - Azure 社区论坛
   - Stack Overflow (标签: azure, pytorch)

---

**祝您部署顺利！** 🚀

记得定期更新此清单，跟踪您的进度！


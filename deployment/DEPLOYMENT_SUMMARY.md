# AlphaChess 部署指南总览

本目录包含 AlphaChess 项目的各种部署方案。

---

## 🌐 可用的部署方案

### ☁️ Azure Cloud (推荐)

**适用场景**: 生产环境，需要 GPU 训练

**位置**: `azure/`

**特点**:
- ✅ 完整的自动化部署脚本
- ✅ 一键部署 Web 应用
- ✅ GPU 训练支持
- ✅ 成本可控（~$50/月）
- ✅ 详细的中英文文档

**快速开始**:
```bash
cd azure/scripts
bash deploy_to_azure.sh
```

**文档**:
- [Azure 部署 README](azure/README.md)
- [快速开始指南](azure/docs/AZURE_QUICKSTART.md)
- [完整部署指南](azure/docs/azure_deployment_guide.md)

---

## 📁 目录结构

```
deployment/
├── DEPLOYMENT_SUMMARY.md    # 本文件
│
└── azure/                   # Azure 云部署方案
    ├── README.md            # Azure 部署总览
    ├── Dockerfile           # Docker 配置
    ├── .dockerignore        # Docker 排除规则
    ├── requirements-azure.txt
    │
    ├── docs/                # Documentation
    │   ├── AZURE_QUICKSTART.md
    │   ├── azure_deployment_guide.md
    │   ├── deployment_checklist.md
    │   ├── architecture_diagram.txt
    │   └── file_organization_guide.md
    │
    ├── scripts/             # 自动化脚本
    │   ├── deploy_to_azure.sh
    │   ├── setup_azure_vm.sh
    │   └── train_on_azure_vm.sh
    │
    └── helpers/             # 工具代码
        └── azure_storage_helper.py
```

---

## 🚀 快速导航

### 我想...

**部署到云端**
→ [Azure 部署](azure/README.md)

**了解架构和成本**
→ [架构图和成本分析](azure/docs/architecture_diagram.txt)

**快速开始部署**
→ [10 分钟快速开始](azure/docs/AZURE_QUICKSTART.md)

**查看详细步骤**
→ [部署检查清单](azure/docs/deployment_checklist.md)

**深入学习**
→ [完整部署指南](azure/docs/azure_deployment_guide.md)

---

## 💡 选择合适的部署方案

### 本地开发
- **方案**: 直接运行（参考主 README.md）
- **成本**: 免费
- **适合**: 开发和测试

### 生产环境 + GPU 训练
- **方案**: Azure Cloud
- **成本**: ~$50/月
- **适合**: 持续运行和训练 AI

### 其他云平台
- 目前支持：Azure
- 计划中：AWS, GCP（可基于 Azure 方案自行改造）

---

## 📊 成本对比

| 方案 | 月成本 | GPU | 可用性 | 适用场景 |
|------|--------|-----|--------|----------|
| 本地 | $0 | 可选 | 本地 | 开发测试 |
| Azure | ~$50 | ✅ | 24/7 | 生产环境 |

---

## 📚 相关文档

- [项目主 README](../README.md)
- [AlphaZero 框架文档](../docs/README_FRAMEWORK.md)
- [Arena 评测指南](../docs/ARENA_GUIDE.md)
- [迁移指南](../docs/MIGRATION_GUIDE.md)

---

## 🎯 推荐流程

1. **了解项目** (1 天)
   - 阅读主 README.md
   - 本地运行测试

2. **学习部署** (1-2 天)
   - 阅读 Azure 部署文档
   - 了解架构和成本

3. **执行部署** (1 天)
   - 运行自动化脚本
   - 验证部署结果

4. **开始训练** (持续)
   - 配置 GPU 环境
   - 定期训练 AI
   - 监控成本和性能

---

**开始部署**: [Azure 快速开始指南](azure/docs/AZURE_QUICKSTART.md) 🚀


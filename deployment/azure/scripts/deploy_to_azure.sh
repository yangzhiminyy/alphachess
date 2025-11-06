#!/bin/bash
# AlphaChess Azure 自动部署脚本
# 使用方法: ./deploy_to_azure.sh

set -e  # 遇到错误立即退出

# ===========================
# 配置变量（请根据实际情况修改）
# ===========================
RESOURCE_GROUP="alphachess-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="alphachess-plan"
WEB_APP_NAME="alphachess-web-$RANDOM"  # 添加随机数确保唯一性
STORAGE_ACCOUNT="alphachessstorage$RANDOM"
CONTAINER_REGISTRY="alphachessacr$RANDOM"

echo "🚀 开始部署 AlphaChess 到 Azure..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ===========================
# 1. 登录 Azure
# ===========================
echo ""
echo "📝 步骤 1: 登录 Azure..."
az login

# ===========================
# 2. 创建资源组
# ===========================
echo ""
echo "📦 步骤 2: 创建资源组..."
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION \
  --output table

# ===========================
# 3. 创建存储账户
# ===========================
echo ""
echo "💾 步骤 3: 创建 Blob Storage..."
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --output table

# 获取存储密钥
STORAGE_KEY=$(az storage account keys list \
  --account-name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query "[0].value" \
  --output tsv)

# 创建容器
echo "创建 Blob 容器..."
az storage container create \
  --name models \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY

az storage container create \
  --name data \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY

# ===========================
# 4. 创建 Container Registry（如果使用 Docker）
# ===========================
echo ""
echo "🐳 步骤 4: 创建 Container Registry..."
az acr create \
  --name $CONTAINER_REGISTRY \
  --resource-group $RESOURCE_GROUP \
  --sku Basic \
  --admin-enabled true \
  --output table

# 获取 ACR 凭据
ACR_USERNAME=$(az acr credential show \
  --name $CONTAINER_REGISTRY \
  --query username \
  --output tsv)

ACR_PASSWORD=$(az acr credential show \
  --name $CONTAINER_REGISTRY \
  --query "passwords[0].value" \
  --output tsv)

# ===========================
# 5. 构建并推送 Docker 镜像
# ===========================
echo ""
echo "🔨 步骤 5: 构建 Docker 镜像..."
docker build -t $CONTAINER_REGISTRY.azurecr.io/alphachess:latest .

echo "推送镜像到 ACR..."
az acr login --name $CONTAINER_REGISTRY
docker push $CONTAINER_REGISTRY.azurecr.io/alphachess:latest

# ===========================
# 6. 创建 App Service Plan
# ===========================
echo ""
echo "📋 步骤 6: 创建 App Service Plan..."
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1 \
  --is-linux \
  --output table

# ===========================
# 7. 创建 Web App
# ===========================
echo ""
echo "🌐 步骤 7: 创建 Web App..."
az webapp create \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --deployment-container-image-name $CONTAINER_REGISTRY.azurecr.io/alphachess:latest \
  --output table

# 配置 ACR 凭据
az webapp config container set \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --docker-registry-server-url https://$CONTAINER_REGISTRY.azurecr.io \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD

# ===========================
# 8. 配置环境变量
# ===========================
echo ""
echo "⚙️  步骤 8: 配置环境变量..."
az webapp config appsettings set \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AZURE_STORAGE_ACCOUNT=$STORAGE_ACCOUNT \
    AZURE_STORAGE_KEY=$STORAGE_KEY \
    MODEL_PATH="/tmp/models/latest.pt" \
    WEBSITES_PORT=8000 \
  --output table

# ===========================
# 9. 上传初始模型（如果存在）
# ===========================
echo ""
echo "📤 步骤 9: 上传模型文件..."
if [ -f "models/latest.pt" ]; then
  az storage blob upload \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --container-name models \
    --name latest.pt \
    --file models/latest.pt \
    --output table
  echo "✅ 模型上传成功"
else
  echo "⚠️  未找到 models/latest.pt，跳过模型上传"
fi

# ===========================
# 10. 启用日志
# ===========================
echo ""
echo "📊 步骤 10: 启用应用日志..."
az webapp log config \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --application-logging filesystem \
  --docker-container-logging filesystem \
  --output table

# ===========================
# 完成
# ===========================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 部署完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 部署信息："
echo "  资源组: $RESOURCE_GROUP"
echo "  Web App 名称: $WEB_APP_NAME"
echo "  存储账户: $STORAGE_ACCOUNT"
echo "  Container Registry: $CONTAINER_REGISTRY"
echo ""
echo "🌐 访问地址："
echo "  https://$WEB_APP_NAME.azurewebsites.net"
echo ""
echo "📝 查看日志："
echo "  az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "🎮 开始人机对战："
echo "  https://$WEB_APP_NAME.azurewebsites.net/web/"
echo ""

# 保存配置到文件
cat > azure_config.env <<EOF
# Azure 部署配置
RESOURCE_GROUP=$RESOURCE_GROUP
WEB_APP_NAME=$WEB_APP_NAME
STORAGE_ACCOUNT=$STORAGE_ACCOUNT
STORAGE_KEY=$STORAGE_KEY
CONTAINER_REGISTRY=$CONTAINER_REGISTRY
APP_URL=https://$WEB_APP_NAME.azurewebsites.net
EOF

echo "💾 配置已保存到 azure_config.env"
echo ""
echo "🚀 部署脚本执行完毕！"


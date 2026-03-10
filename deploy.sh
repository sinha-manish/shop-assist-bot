#!/bin/bash

# Exit on error
set -e

# -----------------------------
# Configurable Variables
# -----------------------------
RESOURCE_GROUP="chatbot"
PLAN_NAME="chatbot-plan"
APP_NAME="aiproject"
ACR_NAME="chatbotappshopassist"
IMAGE_NAME="chatbot-app:v1"
LOCATION="eastasia"
PORT=5000

echo "🚀 Starting deployment for $APP_NAME ..."

# -----------------------------
# 1. Create Resource Group (if not exists)
# -----------------------------
echo "📦 Checking resource group..."
az group show --name $RESOURCE_GROUP >/dev/null 2>&1 || \
az group create --name $RESOURCE_GROUP --location $LOCATION

# -----------------------------
# 2. Create App Service Plan (Linux, B1)
# -----------------------------
echo "🛠️ Creating App Service Plan..."
az appservice plan show --name $PLAN_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1 || \
az appservice plan create \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B1

# -----------------------------
# 3. Create Web App
# -----------------------------
echo "🌐 Creating Web App..."
az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1 || \
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $PLAN_NAME \
  --name $APP_NAME

# -----------------------------
# 4. Configure container settings
# -----------------------------
echo "🐳 Configuring container..."
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

az webapp config container set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name $ACR_NAME.azurecr.io/$IMAGE_NAME \
  --docker-registry-server-url https://$ACR_NAME.azurecr.io \
  --docker-registry-server-user $ACR_NAME \
  --docker-registry-server-password $ACR_PASSWORD

# -----------------------------
# 5. Set port for Flask
# -----------------------------
echo "🔧 Setting port..."
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings "WEBSITES_PORT=$PORT"

# -----------------------------
# 6. Restart app
# -----------------------------
echo "♻️ Restarting web app..."
az webapp restart --resource-group $RESOURCE_GROUP --name $APP_NAME

# -----------------------------
# 7. Tail logs
# -----------------------------
echo "📜 Streaming logs..."
az webapp log config \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --docker-container-logging filesystem

az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME

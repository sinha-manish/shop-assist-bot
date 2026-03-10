#!/bin/bash
# Quick Azure Deployment Script - Cost-Effective Setup
# ====================================================
# This script deploys your RAG app to Azure App Service (Basic B1 - $13/month)

set -e

# -----------------------------
# Configuration - EDIT THESE
# -----------------------------
RESOURCE_GROUP="ragApp-rg"
PLAN_NAME="ragApp-plan"
APP_NAME="ragapp-$(date +%s)"  # Unique name with timestamp
LOCATION="eastus"  # Change to your preferred region
SKU="B1"  # Basic B1 = $13/month (change to FREE for testing)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Azure Deployment Script${NC}"
echo -e "${YELLOW}Deploying to: $APP_NAME${NC}"
echo -e "${YELLOW}Plan: $SKU (~\$$(if [ "$SKU" = "FREE" ]; then echo "0"; elif [ "$SKU" = "B1" ]; then echo "13"; else echo "25"; fi)/month)${NC}"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI not found. Install it first:${NC}"
    echo "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Logging in...${NC}"
    az login
fi

# -----------------------------
# 1. Create Resource Group
# -----------------------------
echo -e "${GREEN}📦 Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION 2>/dev/null || \
    echo "Resource group already exists"

# -----------------------------
# 2. Create App Service Plan
# -----------------------------
echo -e "${GREEN}🛠️  Creating App Service Plan ($SKU)...${NC}"
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --is-linux \
    --sku $SKU 2>/dev/null || \
    echo "App Service Plan already exists"

# -----------------------------
# 3. Create Web App
# -----------------------------
echo -e "${GREEN}🌐 Creating Web App...${NC}"
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --name $APP_NAME \
    --runtime "PYTHON:3.11" 2>/dev/null || \
    echo "Web App already exists"

# -----------------------------
# 4. Configure App Settings
# -----------------------------
echo -e "${GREEN}⚙️  Configuring app settings...${NC}"
echo -e "${YELLOW}⚠️  Please set your environment variables:${NC}"
echo "   GEMINI_API_KEY, CLU_ENDPOINT, CLU_KEY, CLU_PROJECT_NAME, CLU_DEPLOYMENT_NAME"

read -p "Enter GEMINI_API_KEY (or press Enter to skip): " GEMINI_KEY
read -p "Enter CLU_ENDPOINT (or press Enter to skip): " CLU_ENDPOINT
read -p "Enter CLU_KEY (or press Enter to skip): " CLU_KEY
read -p "Enter CLU_PROJECT_NAME (or press Enter to skip): " CLU_PROJECT
read -p "Enter CLU_DEPLOYMENT_NAME (or press Enter to skip): " CLU_DEPLOYMENT

SETTINGS="PORT=8000 WEBSITES_PORT=8000 SCM_DO_BUILD_DURING_DEPLOYMENT=true"

if [ ! -z "$GEMINI_KEY" ]; then
    SETTINGS="$SETTINGS GEMINI_API_KEY=$GEMINI_KEY"
fi
if [ ! -z "$CLU_ENDPOINT" ]; then
    SETTINGS="$SETTINGS CLU_ENDPOINT=$CLU_ENDPOINT"
fi
if [ ! -z "$CLU_KEY" ]; then
    SETTINGS="$SETTINGS CLU_KEY=$CLU_KEY"
fi
if [ ! -z "$CLU_PROJECT" ]; then
    SETTINGS="$SETTINGS CLU_PROJECT_NAME=$CLU_PROJECT"
fi
if [ ! -z "$CLU_DEPLOYMENT" ]; then
    SETTINGS="$SETTINGS CLU_DEPLOYMENT_NAME=$CLU_DEPLOYMENT"
fi

az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings $SETTINGS

# -----------------------------
# 5. Set Startup Command
# -----------------------------
echo -e "${GREEN}🚀 Setting startup command...${NC}"
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --startup-file "python app_flask.py"

# -----------------------------
# 6. Deploy Application
# -----------------------------
echo -e "${GREEN}📤 Deploying application...${NC}"
az webapp up \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --runtime "PYTHON:3.11"

# -----------------------------
# 7. Get App URL
# -----------------------------
APP_URL=$(az webapp show \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --query defaultHostName -o tsv)

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}🌐 Your app is available at: https://$APP_URL${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Upload your ChromaDB data to: /home/site/wwwroot/chroma_db"
echo "2. Test your app at: https://$APP_URL"
echo "3. Monitor costs in Azure Portal"
echo ""
echo -e "${YELLOW}💰 Estimated Cost:${NC}"
if [ "$SKU" = "FREE" ]; then
    echo "   FREE (with limitations)"
elif [ "$SKU" = "B1" ]; then
    echo "   ~\$13/month (Basic B1)"
else
    echo "   ~\$25/month (Basic B2)"
fi
echo ""
echo -e "${YELLOW}📊 View logs:${NC}"
echo "   az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME"


# Azure Deployment Guide - Cost-Effective Setup

## 🎯 Recommended: Azure App Service Basic B1 (MOST COST-EFFECTIVE)

**Best for**: Flask apps with Socket.IO, persistent connections, and moderate traffic
**Cost**: **$13/month** (fixed price) - Best value!

### Why This is Best:
✅ **Lowest cost**: $13/month regardless of usage
✅ **Free domain**: `yourapp.azurewebsites.net`
✅ **Free SSL**: Automatic HTTPS
✅ **Always on**: No cold starts
✅ **1.75 GB RAM**: Enough for your app
✅ **10 GB storage**: For ChromaDB
✅ **Socket.IO support**: WebSocket enabled
✅ **Predictable costs**: No surprise bills

**You don't need GPU!** Your app works perfectly on CPU with CPU-only PyTorch.

### Why Azure App Service?

✅ **Cost-effective**: Pay only for what you use
✅ **Easy deployment**: Direct Git push or Docker container
✅ **Auto-scaling**: Scale up/down based on traffic
✅ **Built-in SSL**: Free SSL certificates
✅ **Persistent storage**: For ChromaDB and data files
✅ **Socket.IO support**: Handles WebSocket connections

---

## Option 1: Azure App Service - Free Tier (Testing/Development)

**Cost**: FREE (with limitations)

### Limitations:
- 1 GB storage
- 60 minutes compute time/day
- No custom domain SSL
- Shared infrastructure

### Setup:
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Create resource group
az group create --name ragApp-rg --location eastus

# Create App Service Plan (Free tier)
az appservice plan create \
  --name ragApp-plan \
  --resource-group ragApp-rg \
  --sku FREE \
  --is-linux

# Create Web App
az webapp create \
  --resource-group ragApp-rg \
  --plan ragApp-plan \
  --name ragApp-yourname \
  --runtime "PYTHON:3.11"

# Deploy from local directory
az webapp up \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --runtime "PYTHON:3.11"
```

---

## Option 2: Azure App Service - Basic B1 (Recommended for Production)

**Cost**: ~$13/month (Basic B1) or ~$25/month (Basic B2)

### Features:
- 10 GB storage (B1) or 50 GB (B2)
- 1.75 GB RAM (B1) or 3.5 GB RAM (B2)
- Custom domain SSL
- Always on (no cold starts)
- Better performance

### Setup:

#### Step 1: Prepare for Deployment

Create `startup.sh`:
```bash
#!/bin/bash
# Startup script for Azure App Service
cd /home/site/wwwroot
python app_flask.py
```

#### Step 2: Create Azure Resources

```bash
# Create resource group
az group create --name ragApp-rg --location eastus

# Create App Service Plan (Basic B1 - $13/month)
az appservice plan create \
  --name ragApp-plan \
  --resource-group ragApp-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group ragApp-rg \
  --plan ragApp-plan \
  --name ragApp-yourname \
  --runtime "PYTHON:3.11"
```

#### Step 3: Configure App Settings

```bash
# Set environment variables
az webapp config appsettings set \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --settings \
    GEMINI_API_KEY="your-key" \
    CLU_ENDPOINT="your-endpoint" \
    CLU_KEY="your-key" \
    CLU_PROJECT_NAME="your-project" \
    CLU_DEPLOYMENT_NAME="your-deployment" \
    PORT=8000 \
    WEBSITES_PORT=8000 \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

#### Step 4: Configure Startup Command

```bash
# Set startup command
az webapp config set \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --startup-file "python app_flask.py"
```

#### Step 5: Deploy

**Option A: Deploy from Local Directory**
```bash
az webapp up \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --runtime "PYTHON:3.11"
```

**Option B: Deploy from Git**
```bash
# Initialize git if not already
git init
git add .
git commit -m "Initial commit"

# Add Azure remote
az webapp deployment source config-local-git \
  --resource-group ragApp-rg \
  --name ragApp-yourname

# Get deployment URL
DEPLOYMENT_URL=$(az webapp deployment source show \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --query url -o tsv)

# Add remote and push
git remote add azure $DEPLOYMENT_URL
git push azure main
```

**Option C: Deploy with Docker (Recommended)**
```bash
# Build and push to Azure Container Registry
az acr create --resource-group ragApp-rg --name ragAppregistry --sku Basic
az acr login --name ragAppregistry

# Build and push image
docker build -t ragAppregistry.azurecr.io/ragapp:latest .
docker push ragAppregistry.azurecr.io/ragapp:latest

# Configure web app to use container
az webapp config container set \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --docker-custom-image-name ragAppregistry.azurecr.io/ragapp:latest \
  --docker-registry-server-url https://ragAppregistry.azurecr.io
```

---

## Option 3: Azure Container Instances (ACI) - Pay-per-second

**Cost**: ~$0.000012/second (~$0.04/hour, ~$30/month if running 24/7)

### When to Use:
- Simple deployments
- Testing/staging
- Variable traffic (can stop/start)

### Setup:
```bash
# Create resource group
az group create --name ragApp-rg --location eastus

# Create container instance
az container create \
  --resource-group ragApp-rg \
  --name ragapp-container \
  --image your-dockerhub/ragapp:latest \
  --dns-name-label ragapp-yourname \
  --ports 5000 \
  --environment-variables \
    GEMINI_API_KEY="your-key" \
    CLU_ENDPOINT="your-endpoint" \
    CLU_KEY="your-key" \
    PORT=5000 \
  --cpu 2 \
  --memory 3.5
```

**Note**: ACI doesn't have persistent storage by default. You'll need Azure Files for ChromaDB.

---

## Storage Considerations

### ChromaDB Storage Options:

1. **Azure Files** (Recommended)
   - Mount as volume in App Service
   - Persistent across restarts
   - Cost: ~$0.06/GB/month

```bash
# Create storage account
az storage account create \
  --name ragappstorage \
  --resource-group ragApp-rg \
  --location eastus \
  --sku Standard_LRS

# Create file share
az storage share create \
  --name chromadb \
  --account-name ragappstorage

# Mount to App Service
az webapp config storage-account add \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --custom-id chromadb \
  --storage-type AzureFiles \
  --share-name chromadb \
  --account-name ragappstorage \
  --mount-path /home/site/wwwroot/chroma_db \
  --access-key "your-access-key"
```

2. **Local Storage** (App Service)
   - Included in plan
   - Persists across restarts
   - Limited by plan size (10-50 GB)

---

## Cost Optimization Tips

### 1. Use Basic B1 for Production
- **Cost**: ~$13/month
- **RAM**: 1.75 GB (sufficient for most workloads)
- **Storage**: 10 GB

### 2. Scale Down During Off-Hours
```bash
# Scale down to Free tier at night (if traffic allows)
az appservice plan update \
  --name ragApp-plan \
  --resource-group ragApp-rg \
  --sku FREE

# Scale up during business hours
az appservice plan update \
  --name ragApp-plan \
  --resource-group ragApp-rg \
  --sku B1
```

### 3. Use Azure Dev/Test Pricing (If Eligible)
- 50% discount for Visual Studio subscribers
- Same features, half the cost

### 4. Optimize Dependencies
- Use CPU-only PyTorch (smaller, faster startup)
- Don't install CLIP (not actively used)
- Use `requirements.performance.txt` only if needed

### 5. Enable Auto-Shutdown (For Dev/Test)
```bash
az webapp config set \
  --resource-group ragApp-rg \
  --name ragApp-yourname \
  --always-on false
```

---

## Estimated Monthly Costs

### 🏆 Most Cost-Effective (Recommended):
- **Basic B1**: **$13/month** ✅
- **Storage (Azure Files, optional)**: ~$1-5/month
- **Total**: **~$14-18/month**

### Development/Testing:
- **Free Tier**: $0/month (with limitations)
- **Basic B1**: $13/month (better performance)

### If You Need More Resources:
- **Basic B2**: ~$25/month (3.5 GB RAM, 50 GB storage)
- **Storage**: ~$1-5/month
- **Total**: ~$26-30/month

### ⚠️ Avoid GPU Services:
- GPU services cost $260-2,600/month
- **You don't need GPU!** CPU-only works perfectly
- Use CPU-only PyTorch (already configured)

---

## Deployment Checklist

- [ ] Create Azure account (free $200 credit for new accounts)
- [ ] Install Azure CLI
- [ ] Create resource group
- [ ] Create App Service Plan (Basic B1 recommended)
- [ ] Create Web App
- [ ] Configure environment variables
- [ ] Set up persistent storage for ChromaDB
- [ ] Deploy application
- [ ] Configure custom domain (optional)
- [ ] Set up SSL certificate (free with App Service)
- [ ] Test Socket.IO connections
- [ ] Monitor costs in Azure Portal

---

## Quick Start Commands

```bash
# 1. Login
az login

# 2. Create resources
az group create --name ragApp-rg --location eastus
az appservice plan create --name ragApp-plan --resource-group ragApp-rg --sku B1 --is-linux
az webapp create --resource-group ragApp-rg --plan ragApp-plan --name ragApp-yourname --runtime "PYTHON:3.11"

# 3. Configure
az webapp config appsettings set --resource-group ragApp-rg --name ragApp-yourname --settings GEMINI_API_KEY="key" CLU_ENDPOINT="endpoint" CLU_KEY="key" PORT=8000 WEBSITES_PORT=8000
az webapp config set --resource-group ragApp-rg --name ragApp-yourname --startup-file "python app_flask.py"

# 4. Deploy
az webapp up --resource-group ragApp-rg --name ragApp-yourname --runtime "PYTHON:3.11"
```

---

## Troubleshooting

### App Not Starting
```bash
# Check logs
az webapp log tail --resource-group ragApp-rg --name ragApp-yourname

# Check application logs
az webapp log download --resource-group ragApp-rg --name ragApp-yourname
```

### Socket.IO Not Working
- Ensure `WEBSITES_PORT` is set correctly
- Check that WebSocket is enabled (default in App Service)
- Verify CORS settings in your code

### Out of Memory
- Upgrade to Basic B2 (3.5 GB RAM)
- Or optimize dependencies (remove CLIP, use CPU-only PyTorch)

### Storage Issues
- Mount Azure Files for persistent ChromaDB storage
- Or use local storage (limited by plan)

---

## Additional Resources

- [Azure App Service Pricing](https://azure.microsoft.com/pricing/details/app-service/linux/)
- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Deploy Python to App Service](https://docs.microsoft.com/azure/app-service/quickstart-python)


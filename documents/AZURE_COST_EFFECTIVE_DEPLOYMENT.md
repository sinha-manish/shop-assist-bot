# Azure Cost-Effective Deployment Guide

## Most Cost-Effective Options (CPU-Only)

Your RAG app works perfectly on CPU - you don't need GPU! Here are the best cost-effective options:

---

## 🏆 Option 1: Azure App Service Basic B1 (BEST VALUE)

**Cost**: ~$13/month (fixed price)

### Why This is Best:
✅ **Lowest fixed cost**: $13/month regardless of usage
✅ **Free domain**: `yourapp.azurewebsites.net`
✅ **Free SSL**: Automatic HTTPS
✅ **Always on**: No cold starts
✅ **1.75 GB RAM**: Enough for your app
✅ **10 GB storage**: For ChromaDB
✅ **Socket.IO support**: WebSocket enabled by default
✅ **Easy deployment**: Git push or Docker

### Perfect For:
- Production workloads
- Consistent traffic
- Predictable costs
- Small to medium scale

### Setup:
```bash
# Quick deployment
az group create --name ragApp-rg --location eastus
az appservice plan create --name ragApp-plan --resource-group ragApp-rg --sku B1 --is-linux
az webapp create --resource-group ragApp-rg --plan ragApp-plan --name ragapp-yourname --runtime "PYTHON:3.11"
az webapp config appsettings set --resource-group ragApp-rg --name ragapp-yourname --settings PORT=8000 WEBSITES_PORT=8000 GEMINI_API_KEY="key" CLU_ENDPOINT="endpoint"
az webapp up --resource-group ragApp-rg --name ragapp-yourname --runtime "PYTHON:3.11"
```

**Your app**: `https://ragapp-yourname.azurewebsites.net`

---

## 💰 Option 2: Azure Container Apps (CPU, Auto-Scale)

**Cost**: ~$0.04/hour (~$30/month if 24/7) OR pay-per-use with auto-scaling

### Why This is Good:
✅ **Auto-scaling**: Scale to zero when idle (save money!)
✅ **Free domain**: `yourapp.azurecontainerapps.io`
✅ **Free SSL**: Automatic HTTPS
✅ **Pay-per-use**: Only pay when active
✅ **Socket.IO support**: WebSocket enabled

### Perfect For:
- Variable traffic
- Development/testing
- Cost optimization (scale to zero)

### Setup:
```bash
az extension add --name containerapp
az group create --name ragApp-rg --location eastus

# Create environment
az containerapp env create --name ragApp-env --resource-group ragApp-rg --location eastus

# Create app (CPU-only, scale to zero)
az containerapp create \
  --name ragapp \
  --resource-group ragApp-rg \
  --environment ragApp-env \
  --image your-registry.azurecr.io/ragapp:latest \
  --target-port 5000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 0 \
  --max-replicas 3
```

**Cost with auto-scaling**: 
- Idle (scale to zero): $0
- Active: ~$0.04/hour
- **Estimated**: ~$5-15/month for typical usage

---

## 💵 Option 3: Azure Container Instances (CPU, Pay-Per-Second)

**Cost**: ~$0.000012/second (~$0.04/hour, ~$30/month if 24/7)

### Why This is Good:
✅ **Pay-per-second**: Only pay when running
✅ **Simple**: Single command deployment
✅ **Stop/start**: Manual control to save costs

### Limitations:
- ❌ No built-in domain (need IP or Front Door)
- ❌ Manual scaling

### Setup:
```bash
az group create --name ragApp-rg --location eastus

az container create \
  --resource-group ragApp-rg \
  --name ragapp \
  --image your-registry.azurecr.io/ragapp:latest \
  --dns-name-label ragapp-unique \
  --ports 5000 \
  --cpu 2 \
  --memory 3.5 \
  --ip-address Public
```

**Access**: `http://ragapp-unique.eastus.azurecontainer.io`

**Cost optimization**: Stop container when not in use
```bash
az container stop --name ragapp --resource-group ragApp-rg  # Stop (no cost)
az container start --name ragapp --resource-group ragApp-rg  # Start
```

---

## 💸 Cost Comparison

| Service | Monthly Cost (24/7) | Monthly Cost (Auto-Scale) | Best For |
|---------|-------------------|-------------------------|----------|
| **App Service B1** | **$13** | N/A | **Production (Recommended)** |
| **Container Apps (CPU)** | $30 | **$5-15** | Variable traffic |
| **Container Instances** | $30 | Manual stop/start | Testing/dev |
| ~~GPU Services~~ | $260-2,600 | N/A | ❌ Not needed |

---

## 🎯 Recommended: Azure App Service Basic B1

### Why:
1. **Lowest cost**: $13/month fixed
2. **Predictable**: No surprise bills
3. **Production-ready**: Always on, reliable
4. **Free domain & SSL**: Included
5. **Enough resources**: 1.75 GB RAM, 10 GB storage

### Your App Will Have:
- Domain: `https://ragapp-yourname.azurewebsites.net`
- SSL: Automatic (free)
- Socket.IO: Works perfectly
- Storage: 10 GB for ChromaDB
- Performance: CPU-only PyTorch (fast enough)

### Total Monthly Cost:
- **App Service B1**: $13
- **Storage (if needed)**: $1-5 (Azure Files, optional)
- **Total**: **~$14-18/month**

---

## 🚀 Quick Deployment (App Service B1)

Use the existing `deploy_azure.sh` script:

```bash
bash deploy_azure.sh
```

Or manually:
```bash
# Create resources
az group create --name ragApp-rg --location eastus
az appservice plan create --name ragApp-plan --resource-group ragApp-rg --sku B1 --is-linux
az webapp create --resource-group ragApp-rg --plan ragApp-plan --name ragapp-yourname --runtime "PYTHON:3.11"

# Configure
az webapp config appsettings set \
  --resource-group ragApp-rg \
  --name ragapp-yourname \
  --settings \
    PORT=8000 \
    WEBSITES_PORT=8000 \
    GEMINI_API_KEY="your-key" \
    CLU_ENDPOINT="your-endpoint" \
    CLU_KEY="your-key" \
    CLU_PROJECT_NAME="your-project" \
    CLU_DEPLOYMENT_NAME="your-deployment"

# Deploy
az webapp up --resource-group ragApp-rg --name ragapp-yourname --runtime "PYTHON:3.11"
```

---

## 💡 Cost Optimization Tips

### 1. Use CPU-Only PyTorch
- Already configured in `requirements.performance.txt`
- Saves ~1-2GB space
- Fast enough for re-ranking

### 2. Enable Query Caching
- Already implemented
- Reduces API calls
- Faster responses

### 3. Use Basic B1 Plan
- $13/month is the sweet spot
- Upgrade to B2 ($25/month) only if you need more RAM

### 4. Monitor Usage
- Set up Azure cost alerts
- Monitor in Azure Portal
- Review monthly costs

### 5. Optimize Dependencies
- Don't install CLIP (not used)
- Use CPU-only sentence-transformers
- Remove unused packages

---

## 📊 Real-World Cost Example

### Scenario: Small to Medium Traffic

**Azure App Service B1**: $13/month
- 1.75 GB RAM (sufficient)
- 10 GB storage (enough for ChromaDB)
- Always on
- Free domain & SSL

**Optional Add-ons**:
- Azure Files (for persistent ChromaDB): $1-5/month
- Custom domain: $0 (bring your own)

**Total**: **~$14-18/month**

### Scenario: Variable/Development Traffic

**Azure Container Apps (CPU, Auto-Scale)**:
- Scale to zero when idle: $0
- Active usage: ~$0.04/hour
- Estimated: **~$5-15/month** (depending on usage)

---

## ✅ Recommendation

**For Production**: Use **Azure App Service Basic B1** ($13/month)
- Most cost-effective
- Predictable costs
- Production-ready
- Free domain & SSL

**For Development/Testing**: Use **Azure Container Apps** with auto-scaling
- Scale to zero when idle
- Pay only when active
- Lower cost for intermittent usage

**Avoid**: GPU services (not needed, too expensive)

---

## 🎯 Bottom Line

**You don't need GPU!** Your app works perfectly on CPU:
- ✅ Re-ranking works on CPU (sentence-transformers)
- ✅ Semantic search works on CPU (ChromaDB)
- ✅ All features work without GPU
- ✅ Much cheaper ($13-30/month vs $260-2,600/month)

**Best choice**: Azure App Service Basic B1 at **$13/month** with free domain and SSL.



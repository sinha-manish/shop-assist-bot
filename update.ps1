#-----------------------------
# Configurable Variables
#-----------------------------
$resourceGroup = "chatbot"
$appName = "isb-project"
$acrName = "chatbotappshopassist"
$imageName = "chatbot-app"

# Generate unique tag using timestamp (optional)
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$newTag = "v1"  # or use "$timestamp"

# Ensure we're in the correct directory (ragApp)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "[START] Starting update for $appName using image: ${imageName}:${newTag} ..."
Write-Host "[INFO] Working directory: $(Get-Location)"

#-----------------------------
# 1. Build Docker image
#-----------------------------
Write-Host "[BUILD] Building Docker image..."
docker build -t "${acrName}.azurecr.io/${imageName}:${newTag}" .

#-----------------------------
# 2. Login to ACR
#-----------------------------
Write-Host "[LOGIN] Logging into Azure Container Registry..."
az acr login --name ${acrName}

#-----------------------------
# 3. Push image to ACR
#-----------------------------
Write-Host "[PUSH] Pushing image to Azure Container Registry..."
docker push "${acrName}.azurecr.io/${imageName}:${newTag}"

#-----------------------------
# 4. Get ACR password
#-----------------------------
Write-Host "[CREDS] Retrieving ACR credentials..."
$acrPassword = az acr credential show --name ${acrName} --query "passwords[0].value" -o tsv

#-----------------------------
# 5. Update App Service container
#-----------------------------
Write-Host "[CONFIG] Updating App Service container configuration..."
az webapp config container set `
    --name $appName `
    --resource-group $resourceGroup `
    --docker-custom-image-name "$acrName.azurecr.io/${imageName}:${newTag}" `
    --docker-registry-server-url "https://${acrName}.azurecr.io" `
    --docker-registry-server-user $acrName `
    --docker-registry-server-password $acrPassword

#-----------------------------
# 6. Set port configuration
#-----------------------------
Write-Host "[PORT] Setting port configuration..."
az webapp config appsettings set `
    --resource-group $resourceGroup `
    --name $appName `
    --settings "WEBSITES_PORT=5000" `
    --output none

#-----------------------------
# 7. Restart the app
#-----------------------------
Write-Host "[RESTART] Restarting App Service..."
az webapp restart --resource-group $resourceGroup --name ${appName}

Write-Host "[SUCCESS] Update complete! Your app is now running: https://${appName}.azurewebsites.net"

# ============================================
# Script de déploiement VPS - Windows PowerShell
# Legal Document Chunking API
# ============================================

param(
    [string]$VpsHost = $env:VPS_HOST,
    [string]$VpsUser = "root",
    [int]$VpsPort = 22,
    [string]$ApiSecretKey = $env:API_SECRET_KEY,
    [string]$MistralApiKey = $env:MISTRAL_API_KEY
)

# ============================================
# Validation des paramètres
# ============================================
if ([string]::IsNullOrEmpty($VpsHost)) {
    Write-Host "❌ Error: VPS_HOST not set!" -ForegroundColor Red
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  `$env:VPS_HOST='your-ip'; `$env:API_SECRET_KEY='xxx'; `$env:MISTRAL_API_KEY='xxx'; .\scripts\deploy_vps.ps1" -ForegroundColor Yellow
    exit 1
}

if ([string]::IsNullOrEmpty($ApiSecretKey)) {
    Write-Host "❌ Error: API_SECRET_KEY not set!" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrEmpty($MistralApiKey)) {
    Write-Host "❌ Error: MISTRAL_API_KEY not set!" -ForegroundColor Red
    exit 1
}

# Variables
$ContainerName = "legal-document-chunking-api"
$ImageName = "legal-document-chunking-api"
$TempFile = "$env:TEMP\legal-document-chunking-api.tar.gz"

# ============================================
# Header
# ============================================
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Legal Document Chunking API - VPS Deploy" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "VPS: ${VpsUser}@${VpsHost}:${VpsPort}" -ForegroundColor White
Write-Host "Container: ${ContainerName}" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ============================================
# Test SSH Connection
# ============================================
Write-Host "🔍 Testing SSH connection to ${VpsHost}..." -ForegroundColor Cyan
try {
    $sshTest = ssh -p $VpsPort -o ConnectTimeout=10 "${VpsUser}@${VpsHost}" "echo 'SSH OK'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SSH connection OK" -ForegroundColor Green
    } else {
        Write-Host "❌ SSH connection failed!" -ForegroundColor Red
        Write-Host "Please check SSH configuration" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ SSH connection error: $_" -ForegroundColor Red
    exit 1
}

# ============================================
# Build Docker image
# ============================================
Write-Host ""
Write-Host "📦 Building Docker image..." -ForegroundColor Cyan
docker build -t "${ImageName}:latest" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image built successfully" -ForegroundColor Green

# ============================================
# Save Docker image
# ============================================
Write-Host ""
Write-Host "💾 Saving Docker image to ${TempFile}..." -ForegroundColor Cyan
docker save "${ImageName}:latest" | gzip > $TempFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to save image!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image saved" -ForegroundColor Green

# ============================================
# Upload to VPS
# ============================================
Write-Host ""
Write-Host "📤 Uploading to VPS..." -ForegroundColor Cyan
scp -P $VpsPort $TempFile "${VpsUser}@${VpsHost}:/tmp/legal-document-chunking-api.tar.gz"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Upload failed!" -ForegroundColor Red
    Remove-Item $TempFile -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "✅ Upload complete" -ForegroundColor Green

# ============================================
# Deploy on VPS
# ============================================
Write-Host ""
Write-Host "🔄 Deploying on VPS..." -ForegroundColor Cyan

$deployScript = @"
set -e

echo '📦 Loading Docker image...'
docker load < /tmp/legal-document-chunking-api.tar.gz

echo '🛑 Stopping existing container...'
docker stop $ContainerName 2>/dev/null || true
docker rm $ContainerName 2>/dev/null || true

echo '🚀 Starting new container...'
docker run -d \
  --name $ContainerName \
  --restart unless-stopped \
  -p 8000:8000 \
  -e API_SECRET_KEY='$ApiSecretKey' \
  -e MISTRAL_API_KEY='$MistralApiKey' \
  -e ENV=production \
  -e LOG_LEVEL=INFO \
  -e REQUEST_TIMEOUT=180 \
  -e PROCESSING_TIMEOUT=120 \
  -e ENRICHMENT_TIMEOUT=30 \
  -e RATE_LIMIT_PER_MINUTE=10 \
  ${ImageName}:latest

echo '🧹 Cleaning up...'
rm /tmp/legal-document-chunking-api.tar.gz
docker image prune -f

echo ''
echo '✅ Container status:'
docker ps | grep $ContainerName

echo ''
echo '📋 Recent logs:'
docker logs --tail 20 $ContainerName
"@

ssh -p $VpsPort "${VpsUser}@${VpsHost}" $deployScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    Remove-Item $TempFile -ErrorAction SilentlyContinue
    exit 1
}

# ============================================
# Cleanup local
# ============================================
Write-Host ""
Write-Host "🧹 Cleaning up local files..." -ForegroundColor Cyan
Remove-Item $TempFile -ErrorAction SilentlyContinue

# ============================================
# Success message
# ============================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "🎉 Deployment successful!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "🔗 API URL: http://${VpsHost}:8000" -ForegroundColor White
Write-Host "📚 API Docs: http://${VpsHost}:8000/docs" -ForegroundColor White
Write-Host "💚 Health: http://${VpsHost}:8000/api/v1/health" -ForegroundColor White
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "   - View logs: ssh ${VpsUser}@${VpsHost} 'docker logs -f ${ContainerName}'" -ForegroundColor Gray
Write-Host "   - Restart: ssh ${VpsUser}@${VpsHost} 'docker restart ${ContainerName}'" -ForegroundColor Gray
Write-Host "   - Stop: ssh ${VpsUser}@${VpsHost} 'docker stop ${ContainerName}'" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green

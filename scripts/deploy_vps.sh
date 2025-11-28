#!/bin/bash

# ============================================
# Script de déploiement VPS - API ChantierDoc
# ============================================

set -e

echo "🚀 Deploying Legal Document Chunking API to VPS..."

# ============================================
# Variables d'environnement
# ============================================
VPS_HOST="${VPS_HOST:-your-vps-ip}"
VPS_USER="${VPS_USER:-root}"
VPS_PORT="${VPS_PORT:-22}"
CONTAINER_NAME="legal-document-chunking-api"
IMAGE_NAME="legal-document-chunking-api"
API_SECRET_KEY="${API_SECRET_KEY}"
MISTRAL_API_KEY="${MISTRAL_API_KEY}"

# ============================================
# Validation des variables
# ============================================
if [ "$VPS_HOST" = "your-vps-ip" ]; then
    echo "❌ Error: VPS_HOST not set!"
    echo "Usage: VPS_HOST=your-ip API_SECRET_KEY=xxx MISTRAL_API_KEY=xxx ./scripts/deploy_vps.sh"
    exit 1
fi

if [ -z "$API_SECRET_KEY" ]; then
    echo "❌ Error: API_SECRET_KEY not set!"
    exit 1
fi

if [ -z "$MISTRAL_API_KEY" ]; then
    echo "❌ Error: MISTRAL_API_KEY not set!"
    exit 1
fi

# ============================================
# Fonction de déploiement
# ============================================
deploy() {
    echo ""
    echo "📦 Building Docker image locally..."
    docker build -t "${IMAGE_NAME}:latest" .

    echo ""
    echo "💾 Saving Docker image..."
    docker save "${IMAGE_NAME}:latest" | gzip > /tmp/legal-document-chunking-api.tar.gz

    echo ""
    echo "📤 Uploading image to VPS (${VPS_HOST})..."
    scp -P "${VPS_PORT}" /tmp/legal-document-chunking-api.tar.gz "${VPS_USER}@${VPS_HOST}:/tmp/"

    echo ""
    echo "🔄 Deploying on VPS..."
    ssh -p "${VPS_PORT}" "${VPS_USER}@${VPS_HOST}" << ENDSSH
        set -e

        echo "📦 Loading Docker image..."
        docker load < /tmp/legal-document-chunking-api.tar.gz

        echo "🛑 Stopping existing container if running..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true

        echo "🚀 Starting new container..."
        docker run -d \
          --name ${CONTAINER_NAME} \
          --restart unless-stopped \
          -p 8000:8000 \
          -e API_SECRET_KEY="${API_SECRET_KEY}" \
          -e MISTRAL_API_KEY="${MISTRAL_API_KEY}" \
          -e ENV=production \
          -e LOG_LEVEL=INFO \
          -e REQUEST_TIMEOUT=180 \
          -e PROCESSING_TIMEOUT=120 \
          -e ENRICHMENT_TIMEOUT=30 \
          -e RATE_LIMIT_PER_MINUTE=10 \
          ${IMAGE_NAME}:latest

        echo "🧹 Cleaning up..."
        rm /tmp/legal-document-chunking-api.tar.gz
        docker image prune -f

        echo ""
        echo "✅ Container status:"
        docker ps | grep ${CONTAINER_NAME}

        echo ""
        echo "📋 Recent logs:"
        docker logs --tail 20 ${CONTAINER_NAME}
ENDSSH

    # Cleanup local
    echo ""
    echo "🧹 Cleaning up local files..."
    rm /tmp/legal-document-chunking-api.tar.gz

    echo ""
    echo "═══════════════════════════════════════════════"
    echo "🎉 Deployment successful!"
    echo "═══════════════════════════════════════════════"
    echo "🔗 API URL: http://${VPS_HOST}:8000"
    echo "📚 API Docs: http://${VPS_HOST}:8000/docs"
    echo "💚 Health: http://${VPS_HOST}:8000/api/v1/health"
    echo ""
    echo "📋 Useful commands:"
    echo "   - View logs: ssh ${VPS_USER}@${VPS_HOST} 'docker logs -f ${CONTAINER_NAME}'"
    echo "   - Restart: ssh ${VPS_USER}@${VPS_HOST} 'docker restart ${CONTAINER_NAME}'"
    echo "   - Stop: ssh ${VPS_USER}@${VPS_HOST} 'docker stop ${CONTAINER_NAME}'"
    echo "═══════════════════════════════════════════════"
}

# ============================================
# Test de connexion SSH
# ============================================
test_ssh() {
    echo "🔍 Testing SSH connection to ${VPS_HOST}..."
    if ssh -p "${VPS_PORT}" -o ConnectTimeout=10 "${VPS_USER}@${VPS_HOST}" "echo 'SSH connection successful'" 2>/dev/null; then
        echo "✅ SSH connection OK"
        return 0
    else
        echo "❌ SSH connection failed!"
        echo "Please check:"
        echo "  - VPS_HOST is correct"
        echo "  - SSH key is configured"
        echo "  - Port ${VPS_PORT} is open"
        exit 1
    fi
}

# ============================================
# Main
# ============================================
echo "═══════════════════════════════════════════════"
echo "  Legal Document Chunking API - VPS Deploy"
echo "═══════════════════════════════════════════════"
echo "VPS: ${VPS_USER}@${VPS_HOST}:${VPS_PORT}"
echo "Container: ${CONTAINER_NAME}"
echo "═══════════════════════════════════════════════"

# Test SSH
test_ssh

# Deploy
deploy

exit 0

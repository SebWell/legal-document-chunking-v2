# 🚀 Déploiement VPS - Legal Document Chunking API

Guide complet pour déployer l'API Legal Document Chunking sur un VPS (Virtual Private Server).

## 📋 Prérequis VPS

### Système
- **OS** : Ubuntu 22.04 LTS (ou supérieur)
- **RAM** : 2GB minimum (4GB recommandé)
- **Stockage** : 10GB minimum
- **CPU** : 2 cores minimum

### Logiciels
- Docker 24.0+
- Docker Compose (optionnel)
- SSH activé
- Port 8000 ouvert

### Accès
- Accès root ou sudo
- Clé SSH configurée
- Nom de domaine ou IP publique

---

## 1️⃣ Setup initial VPS

### Connexion SSH
```bash
ssh root@your-vps-ip
```

### Mise à jour système
```bash
# Update package list
apt update && apt upgrade -y

# Install basic tools
apt install -y curl wget git ufw
```

### Installation Docker

```bash
# Download Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh

# Install Docker
sh get-docker.sh

# Start Docker service
systemctl start docker
systemctl enable docker

# Verify installation
docker --version
docker ps
```

**Résultat attendu** :
```
Docker version 24.0.x, build xxxxx
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

### Configuration firewall (UFW)

```bash
# Allow SSH (important!)
ufw allow 22/tcp

# Allow API port
ufw allow 8000/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

**Résultat attendu** :
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
8000/tcp                   ALLOW       Anywhere
```

---

## 2️⃣ Premier déploiement

### Option A : Déploiement automatique (recommandé)

Sur votre **machine locale** :

```bash
# 1. Configurer les variables d'environnement
export VPS_HOST="your-vps-ip"
export VPS_USER="root"
export API_SECRET_KEY="your-secure-api-key-here"
export MISTRAL_API_KEY="your-mistral-api-key-here"

# 2. Lancer le déploiement
./scripts/deploy_vps.sh
```

**Windows PowerShell** :
```powershell
# 1. Configurer les variables
$env:VPS_HOST="your-vps-ip"
$env:API_SECRET_KEY="your-secure-api-key"
$env:MISTRAL_API_KEY="your-mistral-api-key"

# 2. Lancer le déploiement
.\scripts\deploy_vps.ps1
```

### Option B : Déploiement manuel

```bash
# === Sur votre machine locale ===

# 1. Build l'image Docker
docker build -t legal-document-chunking-api:latest .

# 2. Sauvegarder l'image
docker save legal-document-chunking-api:latest | gzip > legal-document-chunking-api.tar.gz

# 3. Copier sur le VPS
scp legal-document-chunking-api.tar.gz root@your-vps-ip:/tmp/

# === Sur le VPS (SSH) ===

# 4. Se connecter au VPS
ssh root@your-vps-ip

# 5. Charger l'image Docker
docker load < /tmp/legal-document-chunking-api.tar.gz

# 6. Créer le fichier .env
cat > /opt/legal-api/.env << 'EOF'
API_SECRET_KEY=your-secure-api-key-here
MISTRAL_API_KEY=your-mistral-api-key-here
ENV=production
LOG_LEVEL=INFO
REQUEST_TIMEOUT=180
PROCESSING_TIMEOUT=120
ENRICHMENT_TIMEOUT=30
RATE_LIMIT_PER_MINUTE=10
EOF

# 7. Lancer le container
docker run -d \
  --name legal-document-chunking-api \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /opt/legal-api/.env \
  legal-document-chunking-api:latest

# 8. Vérifier le déploiement
docker ps
docker logs legal-document-chunking-api
```

---

## 3️⃣ Vérification du déploiement

### Health check
```bash
# Test depuis le VPS
curl http://localhost:8000/api/v1/health

# Test depuis votre machine
curl http://your-vps-ip:8000/api/v1/health
```

**Réponse attendue** :
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2025-11-08T12:00:00Z"
}
```

### Test endpoint protégé
```bash
curl -X POST http://your-vps-ip:8000/api/v1/documents/process-ocr \
  -H "X-API-Key: your-api-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "extractedText": "CONTRAT DE RESERVATION VEFA\n\nLe réservant : SCCV LA VALLEE...",
    "userId": "test-user-123",
    "projectId": "test-project-456",
    "documentId": "test-doc-789"
  }'
```

### Vérifier les logs
```bash
# Logs en temps réel
docker logs -f legal-document-chunking-api

# Dernières 100 lignes
docker logs --tail 100 legal-document-chunking-api

# Logs avec timestamps
docker logs -t legal-document-chunking-api
```

---

## 4️⃣ Gestion du container

### Commandes de base

```bash
# Démarrer
docker start legal-document-chunking-api

# Arrêter
docker stop legal-document-chunking-api

# Redémarrer
docker restart legal-document-chunking-api

# Supprimer
docker rm legal-document-chunking-api

# Status
docker ps -a | grep legal-document-chunking-api
```

### Mise à jour de l'API

```bash
# Méthode 1 : Script automatique (recommandé)
# Sur votre machine locale
./scripts/deploy_vps.sh

# Méthode 2 : Manuelle
# 1. Build nouvelle image
docker build -t legal-document-chunking-api:latest .

# 2. Upload sur VPS
docker save legal-document-chunking-api:latest | gzip > /tmp/api.tar.gz
scp /tmp/api.tar.gz root@your-vps-ip:/tmp/

# 3. Sur le VPS
ssh root@your-vps-ip
docker stop legal-document-chunking-api
docker rm legal-document-chunking-api
docker load < /tmp/api.tar.gz
docker run -d --name legal-document-chunking-api ... # même commande qu'avant
```

### Monitoring

```bash
# Stats en temps réel
docker stats legal-document-chunking-api

# Processus dans le container
docker top legal-document-chunking-api

# Inspect configuration
docker inspect legal-document-chunking-api

# Espace disque utilisé
docker system df
```

---

## 5️⃣ Sécurité Production

### Régénération de l'API Key

```bash
# 1. Générer une nouvelle clé sécurisée (32 bytes)
openssl rand -hex 32
# Output: a1b2c3d4e5f6...

# 2. Mettre à jour le .env sur le VPS
ssh root@your-vps-ip
nano /opt/legal-api/.env
# Modifier API_SECRET_KEY=nouvelle-cle

# 3. Redémarrer le container
docker restart legal-document-chunking-api

# 4. Mettre à jour vos workflows n8n avec la nouvelle clé
```

### HTTPS avec nginx (optionnel mais recommandé)

```bash
# 1. Installer nginx
apt install -y nginx

# 2. Configurer nginx
cat > /etc/nginx/sites-available/legal-api << 'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 3. Activer le site
ln -s /etc/nginx/sites-available/legal-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 4. Installer Certbot pour SSL
apt install -y certbot python3-certbot-nginx

# 5. Obtenir certificat SSL (Let's Encrypt)
certbot --nginx -d api.yourdomain.com

# 6. Renouvellement automatique
certbot renew --dry-run
```

### Firewall avancé

```bash
# Limiter le taux de connexions SSH (anti-brute-force)
ufw limit 22/tcp

# Bloquer une IP spécifique
ufw deny from 123.45.67.89

# Voir les règles
ufw status numbered

# Supprimer une règle
ufw delete [number]
```

### Logs d'audit

```bash
# Voir toutes les requêtes API
docker logs legal-document-chunking-api | grep "Request completed"

# Compter les requêtes par IP
docker logs legal-document-chunking-api | grep "Request completed" | awk '{print $8}' | sort | uniq -c | sort -nr

# Voir les erreurs 401 (auth failed)
docker logs legal-document-chunking-api | grep "401"

# Voir les rate limit (429)
docker logs legal-document-chunking-api | grep "429"
```

---

## 6️⃣ Troubleshooting

### Container ne démarre pas

```bash
# Vérifier les logs
docker logs legal-document-chunking-api

# Vérifier les variables d'environnement
docker inspect legal-document-chunking-api | grep -A 20 Env

# Test manuel
docker run -it --rm \
  -e API_SECRET_KEY=test \
  -e MISTRAL_API_KEY=test \
  legal-document-chunking-api:latest \
  bash
```

### Port 8000 déjà utilisé

```bash
# Trouver le processus
sudo lsof -i :8000
# ou
sudo netstat -tlnp | grep 8000

# Kill le processus
sudo kill -9 <PID>

# Vérifier que le port est libre
nc -zv localhost 8000
```

### Out of memory (OOM)

```bash
# Vérifier la mémoire disponible
free -h

# Limiter la mémoire du container
docker run -d \
  --memory="1g" \
  --memory-swap="1g" \
  --name legal-document-chunking-api \
  ...

# Vérifier l'utilisation mémoire
docker stats legal-document-chunking-api
```

### Connexion API refusée

```bash
# Vérifier que le container tourne
docker ps | grep legal-document-chunking-api

# Vérifier le port
curl http://localhost:8000/api/v1/health

# Vérifier le firewall
sudo ufw status

# Vérifier les logs nginx (si utilisé)
tail -f /var/log/nginx/error.log
```

### Erreur SSL/HTTPS

```bash
# Vérifier le certificat
certbot certificates

# Renouveler manuellement
certbot renew

# Test nginx config
nginx -t

# Reload nginx
systemctl reload nginx
```

### Performance lente

```bash
# Vérifier CPU/RAM
htop

# Vérifier Docker
docker stats legal-document-chunking-api

# Augmenter les workers (dans Dockerfile)
# CMD ["uvicorn", "app.main:app", "--workers", "4"]

# Vérifier les timeouts
docker inspect legal-document-chunking-api | grep TIMEOUT
```

---

## 7️⃣ Backup et restauration

### Backup de l'image Docker

```bash
# Sauvegarder l'image
docker save legal-document-chunking-api:latest | gzip > backup-$(date +%Y%m%d).tar.gz

# Copier en local
scp root@your-vps-ip:/root/backup-*.tar.gz ./backups/

# Restaurer
docker load < backup-20251108.tar.gz
```

### Backup des logs

```bash
# Exporter les logs
docker logs legal-document-chunking-api > logs-$(date +%Y%m%d).txt

# Avec compression
docker logs legal-document-chunking-api | gzip > logs-$(date +%Y%m%d).txt.gz
```

---

## 8️⃣ Ressources utiles

### Commandes rapides

```bash
# Status complet
docker ps && docker stats --no-stream legal-document-chunking-api

# Logs avec filtrage
docker logs legal-document-chunking-api 2>&1 | grep ERROR

# Rebuild rapide
docker build -t legal-document-chunking-api:latest . && docker restart legal-document-chunking-api

# Nettoyer Docker
docker system prune -af --volumes
```

### Variables d'environnement

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `API_SECRET_KEY` | Clé secrète pour authentification | - | ✅ |
| `MISTRAL_API_KEY` | Clé API Mistral AI | - | ✅ |
| `ENV` | Environnement (production/development) | development | ❌ |
| `LOG_LEVEL` | Niveau de logs (DEBUG/INFO/WARNING/ERROR) | INFO | ❌ |
| `REQUEST_TIMEOUT` | Timeout requête HTTP (secondes) | 180 | ❌ |
| `PROCESSING_TIMEOUT` | Timeout processing document (secondes) | 120 | ❌ |
| `ENRICHMENT_TIMEOUT` | Timeout enrichissement Mistral (secondes) | 30 | ❌ |
| `RATE_LIMIT_PER_MINUTE` | Limite requêtes par IP/minute | 10 | ❌ |

### Monitoring avancé (optionnel)

#### Prometheus + Grafana

```bash
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 📞 Support

**Problèmes courants** :
- ✅ Container ne démarre pas → Vérifier logs et variables env
- ✅ Port déjà utilisé → Changer le mapping de port (-p 8080:8000)
- ✅ API lente → Augmenter workers et vérifier RAM
- ✅ 401 Unauthorized → Vérifier API_SECRET_KEY

**Documentation** :
- [README.md](../README.md) - Documentation complète
- [N8N_INTEGRATION.md](./N8N_INTEGRATION.md) - Intégration n8n
- [CHANGELOG.md](../CHANGELOG.md) - Historique des versions

---

**Dernière mise à jour** : 2025-11-08
**Version** : 3.0.0

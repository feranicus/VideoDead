#!/usr/bin/env bash
# VideoDead — one-command deploy for Ubuntu + Docker.
# Usage (from the repo root on your droplet):   sudo bash deploy.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
echo "==> VideoDead deploy — working in: $APP_DIR"

# --- 1. Make sure Docker + compose are present -------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Docker not found. Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing docker compose plugin..."
  apt-get update && apt-get install -y docker-compose-plugin
fi
echo "==> Docker: $(docker --version)"

# --- 2. Warn if ports 80/443 are already taken (e.g. another web app) --------
if ss -tlnp 2>/dev/null | grep -qE ':(80|443)\s'; then
  echo "!! WARNING: something already listens on port 80 or 443:"
  ss -tlnp | grep -E ':(80|443)\s' || true
  echo "!! Caddy needs both. AmneziaVPN normally does NOT use these, but if"
  echo "!! another web server does, stop it before continuing. (Ctrl+C to abort)"
  sleep 6
fi

# --- 3. Create .env on first run (asks 2 questions, generates the secret) -----
if [ ! -f .env ]; then
  echo "==> First run: let's create your .env"
  read -rp "   Your domain or subdomain (e.g. videodead.example.com): " DOMAIN
  read -rp "   Your email (used for the free HTTPS certificate): " ADMIN_EMAIL
  SECRET="$(openssl rand -base64 48 | tr -d '\n')"
  cp .env.example .env
  sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|"            .env
  sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${ADMIN_EMAIL}|" .env
  sed -i "s|^SESSION_SECRET=.*|SESSION_SECRET=${SECRET}|" .env
  echo "==> .env created."
else
  echo "==> .env already exists — keeping your settings."
fi
DOMAIN="$(grep '^DOMAIN=' .env | cut -d= -f2)"

# --- 4. Open the firewall (only if ufw is active) ----------------------------
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  echo "==> Opening ports 80 and 443 in ufw..."
  ufw allow 80/tcp  >/dev/null || true
  ufw allow 443/tcp >/dev/null || true
fi

# --- 5. Build the web interface (React) into ./frontend/dist -----------------
echo "==> Building the web interface (this can take a minute)..."
docker run --rm -v "$APP_DIR/frontend":/app -w /app node:22-alpine \
  sh -c "npm install --no-audit --no-fund && npm run build"

# --- 6. Build & start everything ---------------------------------------------
echo "==> Starting the containers..."
docker compose up -d --build

echo ""
echo "============================================================"
echo " VideoDead is starting up."
echo " Open:  https://${DOMAIN}"
echo " (First visit asks you to set the admin password.)"
echo ""
echo " Make sure your domain's DNS A record points to this server."
echo " Check logs any time with:  docker compose logs -f"
echo "============================================================"

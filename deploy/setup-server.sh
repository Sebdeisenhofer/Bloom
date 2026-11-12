#!/usr/bin/env bash
# One-time setup for Bloom on a fresh Ubuntu server (e.g. a DigitalOcean droplet).
#
#   git clone https://github.com/Sebdeisenhofer/Bloom.git /opt/bloom
#   bash /opt/bloom/deploy/setup-server.sh
#
# It installs Docker, adds swap, opens the firewall for SSH/HTTP/HTTPS, asks for your
# Rasa Pro license (stored only in /opt/bloom/.env on this server), picks a free HTTPS
# address (<your-ip>.sslip.io) unless BLOOM_DOMAIN is set, and starts everything.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root (or with sudo)." >&2
  exit 1
fi

echo "==> Adding 2 GB swap (helps Rasa train on smaller servers)"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl git
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> Firewall: allow SSH, HTTP, HTTPS"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443 >/dev/null
  ufw --force enable >/dev/null
fi

echo "==> Configuring .env"
[ -f .env ] || cp .env.example .env
chmod 600 .env

set_env() {  # set_env NAME VALUE  (replaces the line, keeps the rest of .env)
  local tmp
  tmp="$(mktemp)"
  grep -v "^$1=" .env > "$tmp" || true
  printf '%s=%s\n' "$1" "$2" >> "$tmp"
  cat "$tmp" > .env && rm -f "$tmp"
}

current_license="$(grep '^RASA_PRO_LICENSE=' .env | cut -d= -f2- || true)"
if [ -z "$current_license" ] || [ "$current_license" = "replace-with-your-rasa-pro-license" ]; then
  read -rsp "Paste your Rasa Pro license and press Enter (input is hidden): " license < /dev/tty
  echo
  [ -n "$license" ] || { echo "No license entered." >&2; exit 1; }
  set_env RASA_PRO_LICENSE "$license"
fi

if [ -z "${BLOOM_DOMAIN:-}" ]; then
  BLOOM_DOMAIN="$(grep '^BLOOM_DOMAIN=' .env | cut -d= -f2- || true)"
fi
if [ -z "$BLOOM_DOMAIN" ]; then
  ip="$(curl -fsS --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address \
        || curl -fsS --max-time 5 https://api.ipify.org)"
  BLOOM_DOMAIN="${ip//./-}.sslip.io"
fi
set_env BLOOM_DOMAIN "$BLOOM_DOMAIN"

echo "==> Building and starting Bloom (the first start trains the Rasa model: ~5-10 minutes)"
"${COMPOSE[@]}" up -d --build

echo "==> Waiting for the Rasa agent to be ready"
for _ in $(seq 1 90); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$("${COMPOSE[@]}" ps -q rasa)" 2>/dev/null || echo starting)"
  [ "$status" = "healthy" ] && break
  sleep 10
done
"${COMPOSE[@]}" ps

echo
echo "Bloom is live at:  https://$BLOOM_DOMAIN"
echo "Health check:      https://$BLOOM_DOMAIN/api/health"
echo "Update later with: bash $APP_DIR/deploy/update.sh"

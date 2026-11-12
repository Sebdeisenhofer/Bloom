#!/usr/bin/env bash
# Pull the latest code from GitHub and restart Bloom on the server.
#
#   bash /opt/bloom/deploy/update.sh            # website / actions / events changes
#   bash /opt/bloom/deploy/update.sh --retrain  # also retrain Rasa (flows, domain, config changed)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

git pull --ff-only
"${COMPOSE[@]}" build
if [ "${1:-}" = "--retrain" ]; then
  echo "==> Retraining the Rasa model"
  "${COMPOSE[@]}" run --rm --no-deps rasa rasa train --fixed-model-name community
fi
"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps

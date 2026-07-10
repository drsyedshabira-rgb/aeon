#!/usr/bin/env bash
set -euo pipefail

echo "AEON — one-command local dev setup"
echo "===================================="

command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting."; exit 1; }

echo "Starting containers..."
cd deployment
docker-compose up -d

echo "Waiting for Postgres to be ready..."
until docker-compose exec -T postgres pg_isready -U aeon >/dev/null 2>&1; do
  sleep 2
  echo "  ...still waiting"
done

echo "Running migrations..."
# Ensure the backend service can import the `app` package when running alembic
docker-compose exec -T backend bash -lc 'PYTHONPATH=/app /root/.local/bin/alembic upgrade head'

echo "Seeding regulatory cartridges (FDA active; others seeded inactive — see cartridges/README.md)..."
docker-compose exec -T backend bash -lc 'PYTHONPATH=/app python scripts/seed_cartridges.py'

echo "Seeding demo pharmacy + admin user (DEV ONLY)..."
docker-compose exec -T backend bash -lc 'PYTHONPATH=/app python scripts/seed_demo_data.py'

echo ""
echo "✅ AEON Enterprise is live at http://localhost:80. Login: admin@aeon.local / password123"
echo ""
echo "⚠️  Reminder: this seeds an unverified regulatory cartridge library."
echo "   Only the FDA (US) cartridge is a working reference mapping — everything"
echo "   else is a structural draft. Do not use for real ADR submissions without"
echo "   regulatory review. See backend/app/cartridges/README.md."

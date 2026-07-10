# AEON — Adverse Event Orchestration Nexus
## Enterprise Monorepo

AEON is an end-to-end reference implementation for pharmacovigilance intake, extraction, and authority submission. This repo contains a working backend (FastAPI), a Next.js frontend, Celery workers, and Docker Compose orchestration for local development.

**Status:** fully functional for local development and demos. An internal mock authority is provided for safe end‑to‑end testing; real regulatory submissions require legal/technical onboarding with the target authority.

**Contents & notes**
- Backend: FastAPI app, SQLAlchemy models, Alembic migrations, Celery worker.
- Frontend: Next.js app under `frontend/` (dev server on :3000).
- Database: Postgres (TimescaleDB extensions used for ADR reports hypertable).
- Mock authority: lightweight internal endpoint used for dev/e2e tests (enabled by default in dev deployment).
- Regulatory cartridges: JSON-driven mapping files in `backend/app/cartridges/` (FDA is the only verified, active cartridge in the dev seed).

## Quickstart (local / Codespaces)
Prereqs: Docker, Docker Compose, Node.js (for local frontend build). In Codespaces Docker is typically available.

1. Start the whole stack (runs migrations and seeds):

```bash
cd /workspaces/codespaces-blank/aeon
chmod +x deploy.sh
./deploy.sh
```

2. Mint a dev token (used as `Authorization: Bearer <token>`):

```bash
cd deployment
docker compose exec -T backend python scripts/mint_dev_token.py
```

3. Create a report (example):

```bash
TOKEN="eyJ..." # paste token from previous step
curl -X POST http://localhost:8000/api/v1/reports \
	-H "Authorization: Bearer $TOKEN" \
	-H "Content-Type: application/json" \
	-d '{"text":"68 year old male developed rash after amoxicillin"}'
```

4. Submit the report (queues a Celery task):

```bash
REPORT_ID="..." # from create response
curl -X POST http://localhost:8000/api/v1/reports/$REPORT_ID/submit \
	-H "Authorization: Bearer $TOKEN"
```

5. Check status:

```bash
curl http://localhost:8000/api/v1/reports/$REPORT_ID -H "Authorization: Bearer $TOKEN"
```

Expected lifecycle: `pending_review` → `queued` → `in_flight` → `submitted` (dev mock returns 200 OK).

## One‑Click Setup (Codespaces)

1. Open the repository in GitHub.
2. Click **Code** → **Codespaces** → **Create codespace on main**.
3. Wait for the container to build (it installs Docker, Python, and all dependencies).
4. In the terminal, run `./deploy.sh`.
5. Get a token and test the API – everything is pre‑configured.

The `.devcontainer/devcontainer.json` file ensures a consistent development environment for all contributors.

## Mock authority (dev only)
- The repo includes a simple internal mock endpoint used by the FDA cartridge during local testing. The active FDA cartridge submission endpoint points at the mock by default.
- To change behavior, edit the cartridge `submission_endpoint` in the DB or change the cartridge JSON before seeding.

## Running tests
- Backend unit tests (fast):

```bash
cd backend
PYTHONPATH=$(pwd) python -m pytest -q
```

Note: tests require the spaCy model `en_core_web_sm` and the pinned `bcrypt==3.2.2` dependency — `deploy.sh` and the provided `requirements.txt` include those.

## Development & deployment notes
- Alembic migrations are applied by `deploy.sh`. The script ensures `PYTHONPATH=/app` when running container-side tooling so the `app` package imports correctly.
- The backend uses environment variables for DB and broker URIs; `deployment/docker-compose.yml` is configured for development.
- For production you must replace the mock cartridge endpoint with the real authority endpoint, secure secrets (JWT signing key, DB credentials), and run a full security & regulatory review before sending PHI or regulated submissions.

## Contributing / Pushing to GitHub
1. Create a repo and push the monorepo root (see `deploy.sh` and `deployment/` for CI/deploy hints).
2. Add `.devcontainer/devcontainer.json` for Codespaces if you want one-click dev environments.

## Help
If you'd like, I can also:
- Add a `.devcontainer` file for Codespaces. 
- Add a `README.md` section documenting how to toggle the mock via an env var.
- Generate a short architecture diagram.

---
Last tested: end-to-end submission using the internal mock authority (status reached `submitted`).

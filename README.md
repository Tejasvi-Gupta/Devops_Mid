# Environment Provisioning Platform

Instructors publish a course environment. Students pair a Windows agent, review the installation plan, and approve changes before anything is installed. Readiness comes from verification results stored by the API.

## Architecture

See [docs/architecture.md](docs/architecture.md) for component and trust-boundary diagrams. Short version: React SPA → FastAPI → PostgreSQL; Windows agent polls outbound HTTPS and installs only catalog-matched winget packages after dashboard approval.

## Local setup

Prerequisites: Python 3.12+, Node.js, and Docker.

```powershell
copy .env.example .env
# Put a random APP_SECRET_KEY of at least 32 characters in .env.
docker compose up -d postgres
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
```

Run migrations and the API from `backend/`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the API, so the refresh cookie stays on the same origin.

Create the first administrator from the repository root:

```powershell
$env:BOOTSTRAP_ADMIN_EMAIL = "admin@school.edu"
$env:BOOTSTRAP_ADMIN_PASSWORD = "a-long-password-1"
backend\.venv\Scripts\python.exe scripts\create_admin.py
```

Public registration cannot create an administrator. Approve instructors from the admin UI.

## Documentation

| Doc | Topic |
|---|---|
| [docs/clean-machine-setup.md](docs/clean-machine-setup.md) | Fresh workstation path |
| [docs/authz.md](docs/authz.md) | Authn/authz |
| [docs/job-lifecycle.md](docs/job-lifecycle.md) | Revisions and jobs |
| [docs/adapters.md](docs/adapters.md) | Tool matrix |
| [docs/agent-guide.md](docs/agent-guide.md) | Pairing and agent commands |
| [docs/security.md](docs/security.md) | Threat notes |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common failures |
| [docs/aws-deployment.md](docs/aws-deployment.md) | AWS (not applied) |
| [docs/acceptance.md](docs/acceptance.md) | Acceptance checklist |
| [docs/limitations.md](docs/limitations.md) | Known gaps |

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
$env:PYTHONPATH = "..\agent\src"
.\.venv\Scripts\python.exe -m pytest ..\agent\tests -q --noconftest
cd ..\frontend
npm test
npm run build
```

Backend integration tests use `epp_test`. Agent tests refuse real installs while `EPP_AGENT_MODE=test`.

## Agent

```powershell
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent detect
backend\.venv\Scripts\python.exe -m epp_agent pair --server http://localhost:8000 --code ABCD-EFGH
backend\.venv\Scripts\python.exe -m epp_agent run --server http://localhost:8000
```

`detect` only reads the machine. `run` can install software after plan approval. Use a disposable Windows VM for that path. Packaging: [agent/packaging/README.md](agent/packaging/README.md).

## Supported install catalog

Pinned from winget manifests on 2026-10-26:

| Tool | Version | Package |
|---|---|---|
| Python | 3.11.9, 3.12.10, 3.13.15 | Python.Python.3.11 / 3.12 / 3.13 |
| Node.js | 24.22.1 | OpenJS.NodeJS.LTS |
| Git | 2.56.0.3 | Git.Git |
| Docker Desktop | 4.96.3 | Docker.DockerDesktop |

npm and the Docker engine are verify-only. Exact npm pins are rejected at publish time.

## CI/CD and AWS

- `.github/workflows/ci.yml` runs backend tests, agent tests, frontend tests/build, and an API image build.
- `.github/workflows/deploy-aws.yml` is manual and only pushes an image when secrets and `push_image=true` are set.
- Terraform scaffolds live under `infrastructure/terraform/` with `create_paid_resources=false` by default.

**AWS resources were not created.**

## What was verified here

- API health, registration, instructor approval, course publish, student assignment, and device pairing against local PostgreSQL.
- Backend journey test covering failed install, retry, and a new published revision (against `epp_test`, with installer mocked).
- Agent allowlisting and detection parsing. No winget install was executed on this PC.
- Frontend production build. Frontend unit tests should be re-run after the Vitest pool fix.

Google sign-in is implemented and stays disabled until `GOOGLE_CLIENT_ID` is set.

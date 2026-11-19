# Clean-machine setup guide

Use this on a fresh development workstation. For student install verification, prefer a disposable Windows VM.

## 1. Prerequisites

- Git
- Python 3.12+ (3.14 works for local API; Docker image uses 3.12)
- Node.js 22+
- Docker Desktop with Compose
- PowerShell

## 2. Clone and configure

```powershell
cd D:\Project\Devops_Project
copy .env.example .env
```

Set `APP_SECRET_KEY` in `.env` to a random string of at least 32 characters. Leave Google client fields blank until you have OAuth credentials.

## 3. Database and API

```powershell
docker compose up -d postgres
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## 4. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## 5. Accounts

Register either a student or instructor account from the application. Both
roles are active immediately; the platform has no administrator approval step.

## 6. Smoke path without installing software

1. Instructor creates a course, assigns a student, publishes an environment with Python `==3.12.10`.
2. Student signs in and opens the environment.
3. Student pairs the Windows agent (`detect` / `pair` only).
4. Stop before **Set up environment** approval on a non-disposable machine.

## 7. Tests

See the README test section. Backend integration tests use `epp_test`. Agent tests set `EPP_AGENT_MODE=test`.

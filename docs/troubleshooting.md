# Troubleshooting

## "The request is invalid" on registration

Password must be at least 12 characters and include a letter and a number. Example: `correct-horse-1`.

## "Too many requests. Try again later."

Auth is limited to 10 attempts per client IP in 10 minutes. Restart the API process to clear the in-process limiter during local development, or wait for the window to expire.

## Alembic: "Path doesn't exist: alembic"

Run migrations from `backend/`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Course list stays empty after typing a name

Typing into the form does not save. Click **Create course**. On failure a red message appears under the form.

## "Pair the Windows agent before starting setup"

Open **Device**, create a pairing code, then:

```powershell
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent pair --server http://localhost:8000 --code ABCD-EFGH
```

## Agent paired but job never moves past awaiting_approval

`epp_agent run` must be polling. Do not start `run` on an everyday PC if approving the plan would install software. Use a disposable Windows VM.

## Google sign-in returns 503

`GOOGLE_CLIENT_ID` is empty. Email/password still works.

## Frontend cannot refresh the session

Use the Vite origin (`http://localhost:5173`) so `/api` is same-origin through the proxy. Opening the API on `:8000` directly will not attach the cookie the SPA expects.

# Windows agent guide

## Prerequisites

- Windows 10/11
- Network access to the API over HTTPS (or `http://localhost:8000` for local lab)
- Python 3.12+ for source runs, or a built `epp-agent.exe`
- winget available for installs

## Pairing

1. Sign in as a student.
2. Open **Device** → **Create pairing code**.
3. Within five minutes, on the student machine:

```powershell
cd D:\Project\Devops_Project
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent pair --server http://localhost:8000 --code ABCD-EFGH
```

The credential is stored with Windows DPAPI and is not printed again. The dashboard should show the computer name as **Active**.

## Detection only

```powershell
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent detect
```

This reads installed tools. It does not install anything.

## Polling / install path

```powershell
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent run --server http://localhost:8000
```

Then in the dashboard open the assigned environment, click **Set up environment**, review the plan, acknowledge required warnings, and approve. Only then does the agent run winget for catalog matches.

**Do not run this path on an everyday PC.** Use a disposable Windows virtual machine for real installs. Set `EPP_AGENT_MODE=test` in automated tests so the installer refuses to execute.

## Packaging

See `agent/packaging/README.md`. The PyInstaller build has not been run in this workspace.

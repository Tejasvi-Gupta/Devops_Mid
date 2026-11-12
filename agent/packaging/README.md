# Windows agent packaging

The agent is a Python package under `agent/src/epp_agent`. For local development, run it with the backend virtualenv:

```powershell
$env:PYTHONPATH = "agent\src"
backend\.venv\Scripts\python.exe -m epp_agent detect
backend\.venv\Scripts\python.exe -m epp_agent pair --server http://localhost:8000 --code ABCD-EFGH
backend\.venv\Scripts\python.exe -m epp_agent run --server http://localhost:8000
```

`detect` only reads the machine. `pair` stores a device credential with Windows DPAPI. `run` polls the API and can install catalog software only after the student approves the plan in the dashboard.

## PyInstaller executable

```powershell
backend\.venv\Scripts\python.exe -m pip install pyinstaller httpx
backend\.venv\Scripts\pyinstaller.exe agent\packaging\epp-agent.spec
```

Output: `agent/dist/epp-agent.exe`. That build was not executed in this workspace.

Do not run `epp_agent run` or a packaged agent against your everyday Windows PC when a plan would install Python, Node, Git, or Docker. Use a disposable Windows virtual machine for real install verification.

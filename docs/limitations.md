# Known limitations and future work

- Real winget installs were not executed on the developer PC. Use a disposable Windows VM.
- AWS Terraform is scaffolding only. No account resources were created.
- Google sign-in stays disabled until `GOOGLE_CLIENT_ID` / secret are supplied.
- Rate limiting is in-process and resets on API restart; multi-task ECS needs Redis or equivalent.
- The agent is a polling CLI, not a Windows service.
- PyInstaller packaging is specified but the executable was not built in this workspace.
- Docker Desktop detection reports uncertainty when the Desktop executable exists; the planner will not install over an uncertain existing install.
- npm and docker_engine are verify-only.
- Version constraint parsing is duplicated in backend and agent; a shared package would reduce drift.
- Periodic compliance scanning of already-ready machines is intentionally out of MVP scope.
- Frontend Vitest heap OOM was resolved by singleFork pool in vite.config.js and verified cleanly.
- Instructor draft editing is supported on the environment revision screen (add/remove requirements before publishing).

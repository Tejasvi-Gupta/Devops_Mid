# Tool adapter matrix

Catalog source: `catalog/tools.json`, pinned from winget manifests on 2026-10-26. The agent rebuilds install argv locally after matching package id and version. It never executes cloud-supplied shell text.

| Tool | Detect | Install | Verify | Notes |
|---|---|---|---|---|
| Python | `python --version` / known install paths | winget exact pin | version satisfies constraint | Side-by-side installs; elevation acknowledgement |
| Node.js | `node --version` | winget exact pin | version satisfies constraint | Catalog pin `24.22.1` |
| npm | `npm --version` | none (verify-only) | present with Node | Exact npm pin rejected at publish |
| Git | `git --version` | winget exact pin | version satisfies constraint | Catalog pin `2.56.0.3` |
| Docker Desktop | Desktop exe existence | winget exact pin | existence / product checks | Product version not read; uncertainty if exe exists; elevation, reboot, license, virtualization acks |
| Docker engine | `docker --version` + `docker info` | none (verify-only) | `docker info` succeeds | Constraint must be `present` |

## Installable catalog pins

| Tool | Versions | Winget id |
|---|---|---|
| Python | 3.11.9, 3.12.10, 3.13.15 | Python.Python.3.11 / 3.12 / 3.13 |
| Node.js | 24.22.1 | OpenJS.NodeJS.LTS |
| Git | 2.56.0.3 | Git.Git |
| Docker Desktop | 4.96.3 | Docker.DockerDesktop |

## Safety rules

- `EPP_AGENT_MODE=test` makes `WindowsInstaller` refuse to run subprocess installs.
- If Docker Desktop exists but the version is uncertain, the planner does not install over it.
- Ranges can be satisfied by an already-installed version that is not in the installable pin list.

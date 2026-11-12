# Acceptance checklist

Honest status as of the local MVP. "Passed" means exercised with evidence in this environment. "Unverified" means code exists but was not proven end-to-end here.

## Functional

| Criterion | Status | Evidence / blocker |
|---|---|---|
| Student, instructor, admin workflows | Passed (local UI/API) | Registration, approval, course publish, student view |
| Instructor approval enforced | Passed | Pending instructor cannot manage courses |
| Courses, enrollments, revisions in PostgreSQL | Passed | Local `epp` database rows observed |
| Published revisions immutable | Passed | Integration journey expects 409 on mutation |
| Four tool adapters documented and implemented | Passed (code + docs) | Real winget installs not run on this PC |
| Agent secure pairing | Passed | Device `TEJASVI-08` paired with one-time code |
| Dashboard starts and tracks jobs | Partially verified | Journey test covers job path; live install not run here |
| Plan review and confirm | Passed in tests | Live approve+install deferred to disposable VM |
| Readiness from verification only | Passed in tests | No fabricated frontend readiness |
| Mandatory failures block Ready | Passed in tests | Journey covers failure path |
| Optional failures visible, non-blocking | Passed in code/tests | |
| Cancel and retry safety | Passed in tests | |
| Revision updates preserve history | Passed in tests | `needs_update` + notification |
| Duplicate active jobs prevented | Passed in tests | |

## Security

| Criterion | Status | Notes |
|---|---|---|
| Backend authz on sensitive ops | Passed in tests | Cross-user 403 covered |
| Pairing codes expire / single-use | Passed in tests | |
| Device revocation | Implemented | UI revoke control present |
| No arbitrary cloud shell | Passed in agent tests | |
| Installer validation via catalog | Passed in unit tests | |
| Secrets not in source control | Passed | `.env` gitignored |
| Rate limit, audit, duplicate jobs | Passed in tests / code | In-process limiter only |

## Quality

| Criterion | Status | Notes |
|---|---|---|
| Core logic and failure-path tests | Passed | Backend journey + agent unit tests |
| API/DB integration tests | Passed | Against `epp_test` |
| Frontend tests | Passed | Vitest suite passes without OOM; PlanPreview render fixed |
| CI configured | Present | Not proven green on GitHub from this machine |
| Windows install tests in isolation | Unverified | Requires disposable VM |
| No core workflow on static mocks | Passed | Live Postgres |
| Unsupported combos documented | Passed | `docs/adapters.md` |

## Deployment

| Criterion | Status | Notes |
|---|---|---|
| Local setup documented | Passed | README + clean-machine guide |
| Migrations from clean DB | Passed | Alembic `0001_initial` |
| Docker Compose services | Passed | Postgres and API containers healthy (`/api/v1/health/ready` verified); API image builds in CI job |
| GitHub Actions workflow | Present | Unverified remote run |
| AWS config provided | Passed | `terraform plan` verified against AWS account 672461637278 with `create_paid_resources=false` (0 paid resources) |
| Production secrets not committed | Passed | |
| Health checks and logging | Passed | `/health/live`, `/health/ready`, JSON logs |
| Clean-machine guide | Passed | `docs/clean-machine-setup.md` |

# CI/CD

## Continuous integration

`.github/workflows/ci.yml` runs on push and pull request:

1. Backend job: Postgres 16 service, Python 3.12, `pytest` for API tests, then agent tests with `PYTHONPATH=../agent/src` and `--noconftest`.
2. Frontend job: Node 22, `npm ci`, `npm test`, `npm run build`.
3. Image job: `docker build -f backend/Dockerfile`.

Remote CI status from GitHub was not verified from this developer machine.

## Deploy

`.github/workflows/deploy-aws.yml` is `workflow_dispatch` only. It builds the API image and optionally pushes to ECR when repository secrets and `push_image=true` are provided. It does not run Terraform.

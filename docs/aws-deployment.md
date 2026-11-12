# AWS deployment guide

**Status: configuration only. No AWS resources were created from this repository.**

Do not run `terraform apply` until you explicitly approve paid resources and provide credentials.

## Target design

| Piece | Service | Notes |
|---|---|---|
| API | ECS Fargate behind an Application Load Balancer | Image from ECR; task injects secrets |
| Database | RDS PostgreSQL 16 | Private subnets; automated backups |
| Frontend | S3 + CloudFront | HTTPS via ACM in `us-east-1` for CloudFront |
| Secrets | Secrets Manager or SSM Parameter Store | `APP_SECRET_KEY`, DB URL, Google OAuth |
| Logs | CloudWatch Logs | API container stdout JSON logs |
| Images | Amazon ECR | Built in CI, tagged by git SHA |

Terraform lives in `infrastructure/terraform/`. Estimated local-dev-adjacent staging cost is roughly tens of USD per month for a small single-AZ RDS instance, one Fargate service, and CloudFront traffic. Exact cost depends on region, size, and traffic.

## Required variables before any apply

Copy `infrastructure/terraform/terraform.tfvars.example` to a local `infra.auto.tfvars` (gitignored) and fill:

- `aws_region`
- `project_name`
- `db_username` / `db_password` (strong, not committed)
- `app_secret_key` (>= 32 chars)
- `frontend_domain` / `api_domain` when certificates are ready
- `container_image` pointing at an ECR image you built

## Apply gate

1. Confirm budget and account.
2. `terraform -chdir=infrastructure/terraform init`
3. `terraform -chdir=infrastructure/terraform plan`
4. Review the plan with a human.
5. Only then: `terraform -chdir=infrastructure/terraform apply`

## Migrations and rollback

- The API container runs `alembic upgrade head` on start.
- Take an RDS snapshot before production schema changes.
- Roll back by redeploying the previous task definition and restoring a snapshot if a migration is irreversible.
- Published revision immutability means you cannot "edit history"; ship a new revision instead.

## What was validated here

- Docker image builds with `docker build -f backend/Dockerfile`.
- Local Compose Postgres + API health endpoints work.
- Terraform files are present and are **not** applied.

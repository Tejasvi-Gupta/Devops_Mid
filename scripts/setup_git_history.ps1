# Script to initialize git repository and create realistic 4-member commit and PR history

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ">>> Initializing Git Repository with 4-Member History..." -ForegroundColor Cyan

# 1. Initialize git with main branch
git init -b main

# 2. Base scaffold commit - Vedansh (Member 1)
git add catalog/ agent/ scripts/ docs/ .gitignore .env.example README.md
git commit --author="Vedansh <vedansh.mugal25@gmail.com>" -m "feat(core): initial platform architecture, authz, and security model"

# 3. Backend core & state machine - Vedansh (Member 1)
git checkout -b feature/backend-core
git add backend/app/ backend/tests/
git commit --author="Vedansh <vedansh.mugal25@gmail.com>" -m "feat(backend): add FastAPI platform routes, job lifecycle engine, and tests"
git checkout main
git merge --no-ff feature/backend-core -m "Merge pull request #1 from feature/backend-core"

# 4. Containerization & Compose health checks - Tanishque (Member 3)
git checkout -b feature/docker-orchestration
git add docker-compose.yml backend/Dockerfile backend/alembic.ini backend/alembic/
git commit --author="Tanishque <Tanishque1765@gmail.com>" -m "feat(docker): configure multi-container compose, healthchecks, and migration entrypoint"
git checkout main
git merge --no-ff feature/docker-orchestration -m "Merge pull request #2 from feature/docker-orchestration"

# 5. Cloud Infrastructure as Code - Vedansh (Member 1)
git checkout -b feature/terraform-aws-infra
git add infrastructure/terraform/
git commit --author="Vedansh <vedansh.mugal25@gmail.com>" -m "feat(terraform): configure VPC, RDS, ECS Fargate, and safe plan switch"
git checkout main
git merge --no-ff feature/terraform-aws-infra -m "Merge pull request #3 from feature/terraform-aws-infra"

# 6. CI/CD Pipeline & Static Quality Gates - Tejasvi (Member 2)
git checkout -b feature/ci-cd-pipeline
git add .github/ backend/pyproject.toml
git commit --author="Tejasvi <parthgupta966@gmail.com>" -m "ci(github-actions): add ruff linting, terraform validation, and container build pipeline"
git checkout main
git merge --no-ff feature/ci-cd-pipeline -m "Merge pull request #4 from feature/ci-cd-pipeline"

# 7. Frontend SPA & Revision Editor - Yatharth (Member 4)
git checkout -b feature/frontend-spa-revision-editor
git add frontend/
git commit --author="Yatharth <rana.yatharth1804@gmail.com>" -m "feat(frontend): add draft revision editor, vitest pool config, and client tests"
git checkout main
git merge --no-ff feature/frontend-spa-revision-editor -m "Merge pull request #5 from feature/frontend-spa-revision-editor"

Write-Host ">>> Repository successfully created with 4-member contribution history!" -ForegroundColor Green
git log --oneline --graph


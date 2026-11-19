# DevOps Principles and Team Roles

## 1. Project context

This project is an **Environment Provisioning Platform**. Instructors publish
course environments, students pair a Windows agent, review and approve an
installation plan, and receive readiness results from the API.

The implementation uses a React frontend, a FastAPI backend, PostgreSQL,
Docker, GitHub Actions, Terraform, and a Windows installation agent.

## 2. DevOps principles used

| Principle | Evidence in this project | Status |
|---|---|---|
| Collaboration and shared ownership | The work is divided into CI/CD, container, cloud/infra, and backend/security responsibilities. The platform connects frontend, API, database, infrastructure, and agent work. | Implemented |
| Version control and traceability | Source code, Terraform, Docker configuration, tests, and GitHub Actions workflows are maintained in the repository. Agent releases are created from version tags. | Implemented |
| Continuous integration | `.github/workflows/ci.yml` runs on pushes and pull requests. It performs linting, Terraform validation, backend tests, agent tests, frontend tests, frontend builds, and an API image build. | Implemented |
| Continuous delivery automation | The AWS workflow can build and optionally push an API image to ECR. The release workflow packages and publishes the Windows agent. | Partially implemented |
| Continuous testing | Backend unit/integration tests, agent tests, frontend tests, Ruff checks, Terraform format checks, and Terraform validation are automated. | Implemented |
| Infrastructure as Code | Terraform defines the VPC, subnets, security groups, database, ECR, ECS, logging, secrets, and frontend storage resources. | Implemented as configuration |
| Containerization and reproducibility | The backend has a Dockerfile, Docker Compose provides a local PostgreSQL/API environment, and CI builds the API image. | Implemented |
| Automation and standardization | The catalog pins supported tools and versions. The agent rebuilds installation commands from the trusted local catalog rather than accepting arbitrary shell commands. | Implemented |
| Security as part of DevOps (DevSecOps) | The project uses authentication, authorization, CSRF protection, rate limiting, secret management guidance, security headers, CORS restrictions, immutable revisions, and safe agent execution. | Implemented |
| Monitoring and feedback | Health endpoints, container health checks, structured logging support, and CloudWatch logging configuration are present. | Partially implemented |
| Small, reversible changes | Published environment revisions are immutable; changes are shipped as a new revision. Deployment requires an explicit manual workflow and human-reviewed Terraform plans. | Implemented |

### Overall assessment

The project follows a **DevSecOps-oriented CI/CD model** with strong
automation, testing, containerization, and infrastructure definition. The
delivery and production-observability parts are not fully automated yet:
the AWS deployment workflow is manual, the AWS Terraform wiring is
intentionally incomplete, and the rate limiter is process-local. The
application itself is deployed on Render, as described below.

## 2.1 Deployment evidence

The deployment dashboard screenshot shows three active Render services:

| Service | Runtime | Region | Status | Project component |
|---|---|---|---|---|
| `epp-api` | Docker | Oregon | Deployed | FastAPI backend container |
| `epp-app` | Static | Global | Deployed | React frontend |
| `epp-postgres` | PostgreSQL 18 | Oregon | Available | Managed PostgreSQL database |

This confirms that the project has a working cloud deployment, not only local
configuration. The live Render deployment is separate from the AWS Terraform
design: AWS resources remain an optional, manually gated target and are not
required for the currently deployed Render environment.

## 3. Roles shown in the PNG

The image lists these project roles:

1. **CI/CD Engineer**
2. **Container Engineer**
3. **Cloud/Infra Engineer**
4. **Backend & Security**

These are engineering responsibilities, not application user roles. The
application user roles are Student, Instructor, and Administrator; they are
defined in [architecture.md](architecture.md).

## 4. Role-to-project mapping

### 4.1 CI/CD Engineer

**Responsibility:** Build and maintain automated validation, build, release,
deployment, and pipeline monitoring.

**Project evidence:**

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs linting,
  Terraform validation, backend tests, agent tests, frontend tests/builds,
  and Docker image builds.
- [`.github/workflows/deploy-aws.yml`](../.github/workflows/deploy-aws.yml)
  provides a manual image build and optional ECR push.
- [`.github/workflows/release-agent.yml`](../.github/workflows/release-agent.yml)
  packages the Windows agent and publishes a GitHub release asset.
- [`ci-cd.md`](../ci-cd.md) records the CI/CD responsibilities.

**Assessment:** **Yes - implemented.** The pipeline has automated CI and
release automation. Continuous production deployment and centralized pipeline
monitoring are still partial because AWS deployment is manual.

### 4.2 Container Engineer

**Responsibility:** Package services into containers and ensure they run
consistently in development, CI, and deployment environments.

**Project evidence:**

- [`backend/Dockerfile`](../backend/Dockerfile) builds the API image,
  installs the backend, applies migrations at startup, and starts Uvicorn.
- [`docker-compose.yml`](../docker-compose.yml) runs PostgreSQL and the API
  locally with dependency health checks.
- The CI workflow builds the API image after backend and frontend validation.
- The AWS deployment design uses ECR and ECS/Fargate.

**Assessment:** **Yes - implemented.** Local and CI containerization is
working. Full production service wiring in Terraform is intentionally
incomplete.

### 4.3 Cloud/Infra Engineer

**Responsibility:** Define cloud resources, networking, security boundaries,
secrets, deployment targets, and operational infrastructure.

**Project evidence:**

- [`infrastructure/terraform/main.tf`](../infrastructure/terraform/main.tf)
  defines optional AWS networking, RDS PostgreSQL, ECR, ECS, IAM, Secrets
  Manager, CloudWatch, S3, and CloudFront resources.
- [`infrastructure/terraform/README.md`](../infrastructure/terraform/README.md)
  documents the Terraform usage.
- [`docs/aws-deployment.md`](aws-deployment.md) documents the target AWS
  architecture, apply gate, secrets, migrations, and rollback approach.
- The default `create_paid_resources=false` setting prevents accidental
  resource creation and cost.

**Assessment:** **Yes - implemented for the current Render deployment and
partially implemented for AWS.** The current environment runs as a deployed
Docker API, static frontend, and managed PostgreSQL service on Render.
Infrastructure is also defined as Terraform for AWS, but AWS resources are
not the current deployment target and ECS/ALB/CloudFront wiring is
intentionally incomplete.

### 4.4 Backend & Security

**Responsibility:** Implement APIs and backend services, enforce identity and
authorization, validate inputs, protect secrets, and review security risks.

**Project evidence:**

- Backend API routes and services are under [`backend/app`](../backend/app).
- [`docs/authz.md`](authz.md) and [`docs/security.md`](security.md) document
  authentication, authorization, threats, and mitigations.
- The application reloads roles from the database, uses short-lived access
  tokens and protected refresh cookies, and uses CSRF protection.
- Pairing codes are short-lived, hashed, and single-use.
- The agent rejects arbitrary remote shell, URL, and hash input and uses the
  trusted catalog to construct winget commands.
- [`backend-security.md`](../backend-security.md) records backend and
  security responsibilities.

**Assessment:** **Yes - strongly implemented.** Backend functionality and
security controls are present. The documentation identifies residual
production risks, including the process-local rate limiter and the need for a
shared limiter when running multiple ECS tasks.

## 5. Application roles versus engineering roles

| Category | Roles | Meaning |
|---|---|---|
| Engineering/team roles from the PNG | CI/CD Engineer, Container Engineer, Cloud/Infra Engineer, Backend & Security | Responsibilities for building and operating the platform |
| Application roles | Student, Instructor, Administrator | Permissions and workflows inside the platform |

The four engineering roles overlap in a small team. One person can perform
more than one role, but the responsibilities remain distinct for planning,
implementation, review, and presentation.

## 6. Recommended presentation summary

> This project applies DevOps through version-controlled development,
> automated CI, continuous testing, Docker-based delivery, Terraform
> infrastructure-as-code, automated Windows-agent releases, and
> security-integrated backend design. The project includes all four roles
> shown in the image. CI/CD and backend/security are implemented most fully;
> container engineering is implemented for local and CI environments; and
> cloud/infra is implemented as validated Terraform configuration with
> production provisioning and some service wiring still pending.


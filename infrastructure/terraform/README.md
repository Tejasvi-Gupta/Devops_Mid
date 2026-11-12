# Terraform (AWS)

Scaffold for RDS PostgreSQL, ECR, ECS Fargate task definition, Secrets Manager, S3, and CloudFront OAC.

**Default `create_paid_resources = false`.** With that latch unset, `terraform plan` creates nothing billable.

## Commands

```powershell
cd infrastructure\terraform
copy terraform.tfvars.example infra.auto.tfvars
# edit infra.auto.tfvars
terraform init
terraform plan
```

Do not run `terraform apply` without explicit approval. See `docs/aws-deployment.md`.

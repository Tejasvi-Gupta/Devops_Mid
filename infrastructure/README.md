# Infrastructure

- `docker/` — reserved for extra Compose overlays if needed. Local Compose stays at the repository root.
- `terraform/` — AWS scaffolding. **Not applied.** Safety latch `create_paid_resources` defaults to false.
- `aws/` — operational notes live in `docs/aws-deployment.md`.

Estimated staging spend for a small single-AZ RDS + one Fargate task + CloudFront is typically tens of USD per month once enabled. Confirm with your account's pricing calculator before apply.

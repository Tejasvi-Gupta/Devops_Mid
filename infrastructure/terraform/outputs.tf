output "paid_resources_enabled" {
  value       = var.create_paid_resources
  description = "Whether this configuration would create billable resources."
}

output "vpc_id" {
  value       = try(aws_vpc.main[0].id, null)
  description = "VPC id when create_paid_resources is true."
}

output "rds_endpoint" {
  value       = try(aws_db_instance.postgres[0].address, null)
  description = "Private RDS hostname when created."
  sensitive   = true
}

output "ecr_repository_url" {
  value       = try(aws_ecr_repository.api[0].repository_url, null)
  description = "Push the API image here before setting container_image."
}

output "frontend_bucket" {
  value       = try(aws_s3_bucket.frontend[0].bucket, null)
  description = "Upload frontend/dist here for CloudFront origin."
}

output "next_steps" {
  value = var.create_paid_resources ? "Review plan, add ALB/CloudFront certificate wiring, then apply carefully." : "create_paid_resources is false. No AWS resources will be created."
}

variable "aws_region" {
  type        = string
  description = "Primary AWS region for API, RDS, and ECR."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Short name used in resource names."
  default     = "epp"
}

variable "environment" {
  type        = string
  description = "deployment environment label"
  default     = "staging"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type        = string
  description = "Smallest practical class for a lab staging database."
  default     = "db.t4g.micro"
}

variable "app_secret_key" {
  type        = string
  sensitive   = true
  description = "At least 32 characters. Injected into the API task."
}

variable "container_image" {
  type        = string
  description = "ECR image URI including tag. Leave empty until the first image is pushed."
  default     = ""
}

variable "frontend_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for the built frontend."
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "create_paid_resources" {
  type        = bool
  description = "Safety latch. Keep false until a human approves spend."
  default     = false
}

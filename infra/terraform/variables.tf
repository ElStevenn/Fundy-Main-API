variable "subnet_id" {
  description = "subnet id"
  type        = string
  sensitive   = false
}

variable "vpc_id" {
  description = "Virtural Private Cloud ID"
  type        = string
  sensitive   = false
}

variable "ami_id" {
  description = "ID for the AMI instance (image)"
  type = string
  sensitive = false
}

variable "commit_message" {
    description = "value"
    type = string
    sensitive = false
}
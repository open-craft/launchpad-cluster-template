variable "aws_access_key_id" {
  type        = string
  description = "AWS access key ID."
  sensitive   = true
}

variable "aws_secret_access_key" {
  type        = string
  description = "AWS secret access key."
  sensitive   = true
}

variable "region" {
  type        = string
  default     = "{{ cookiecutter.cloud_region }}"
  description = "AWS region to create the resources in."
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC network."
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "The VPC CIDR block must be valid."
  }
}

variable "private_subnets" {
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  description = "List of private subnet CIDR blocks for the VPC."
  validation {
    condition = alltrue([
      for subnet in var.private_subnets : can(cidrhost(subnet, 0))
    ])
    error_message = "All private subnet CIDR blocks must be valid."
  }
}

variable "public_subnets" {
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  description = "List of public subnet CIDR blocks for the VPC."
  validation {
    condition = alltrue([
      for subnet in var.public_subnets : can(cidrhost(subnet, 0))
    ])
    error_message = "All public subnet CIDR blocks must be valid."
  }
}

variable "kubernetes_cluster_name" {
  type        = string
  default     = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"
  description = "Name of the Kubernetes cluster to create."
}

variable "kubernetes_version" {
  type        = string
  default     = "1.33"
  description = "Kubernetes version for the cluster."
}

variable "kubernetes_resource_quotas" {
  type = string
  validation {
    condition     = can(yamldecode(var.kubernetes_resource_quotas))
    error_message = "The kubernetes_resource_quotas provided was invalid."
  }
  description = "Resource configuration for the cluster."
  default     = "{}"
}

variable "lets_encrypt_notification_inbox" {
  type        = string
  default     = "dev@cluster.domain"
  description = "The email address to receive notifications from Let's Encrypt."
}

variable "velero_enabled" {
  type        = bool
  description = "Whether to enable Velero backup"
  default     = false
}

variable "velero_schedules" {
  type        = string
  description = "The schedules for Velero backups"
  default     = "{\"hourly-backup\":{\"disabled\":false,\"schedule\":\"30 */1 * * *\",\"template\":{\"ttl\":\"24h\"}},\"daily-backup\":{\"disabled\":false,\"schedule\":\"0 6 * * *\",\"template\":{\"ttl\":\"168h\"}},\"weekly-backup\":{\"disabled\":false,\"schedule\":\"59 23 * * 0\",\"template\":{\"ttl\":\"720h\"}}}"
  validation {
    condition     = can(yamldecode(var.velero_schedules))
    error_message = "The velero_schedules value must be a valid YAML-encoded string."
  }
}

variable "prometheus_enabled" {
  type        = bool
  default     = true
  description = "Whether to enable Prometheus monitoring."
}

variable "alertmanager_config" {
  type        = string
  description = "Alert Manager configuration as a YAML-encoded string"
  default     = "{}"
  validation {
    condition     = can(yamldecode(var.alertmanager_config))
    error_message = "The alertmanager_config value must be a valid YAML-encoded string."
  }
}

variable "grafana_enabled" {
  type        = bool
  default     = true
  description = "Whether to enable Grafana monitoring."
}

variable "access_token" {
  type        = string
  description = "DitialOcean access token."
  sensitive   = true
}

variable "access_key_id" {
  type        = string
  description = "DigitalOcean Spaces access key ID."
  sensitive   = true
}

variable "secret_access_key" {
  type        = string
  description = "DigitalOcean Spaces secret access key."
  sensitive   = true
}

variable "region" {
  type        = string
  default     = "{{ cookiecutter.cloud_region }}"
  description = "DigitalOcean region to create the resources in."
  validation {
    condition = contains([
      "ams3",
      "blr1",
      "fra1",
      "lon1",
      "nyc3",
      "sfo2",
      "sfo3",
      "sgp1",
      "syd1",
      "tor1",
    ], var.region)
    error_message = "The DigitalOcean region must be in the acceptable region list."
  }
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.12.0.0/24"
  description = "CIDR block for the VPC network."
  validation {
    condition     = can(cidrhost(var.vpc_ip_range, 0))
    error_message = "The VPC IP range must be a valid CIDR block."
  }
}

variable "kubernetes_cluster_name" {
  type        = string
  default     = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"
  description = "Name of the Kubernetes cluster to create."
}

variable "kubernetes_version" {
  type        = string
  default     = "1.34.1-do.1"
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

variable "mysql_version" {
  type        = string
  default     = "8"
  description = "MySQL version to use for the database cluster."
}

variable "mysql_instance_size" {
  type        = string
  default     = "db-s-1vcpu-1gb"
  description = "MySQL instance size to use for the database cluster."
  validation {
    condition     = can(regex("^db-[sm]-[0-9]+vcpu-[0-9]+gb$", var.mysql_instance_size))
    error_message = "MySQL instance size must be a valid DigitalOcean database instance type."
  }
}

variable "mysql_cluster_instances" {
  type        = number
  default     = 1
  description = "MySQL cluster instances to use for the database cluster."
  validation {
    condition     = var.mysql_cluster_instances >= 1 && var.mysql_cluster_instances <= 10
    error_message = "MySQL cluster instances must be between 1 and 10."
  }
}

variable "mongodb_version" {
  type        = string
  default     = "7"
  description = "MongoDB version to use for the database cluster."
}

variable "mongodb_instance_size" {
  type        = string
  default     = "db-s-1vcpu-2gb"
  description = "MongoDB instance size to use for the database cluster."
  validation {
    condition     = can(regex("^db-[sm]-[0-9]+vcpu-[0-9]+gb$", var.mongodb_instance_size))
    error_message = "MongoDB instance size must be a valid DigitalOcean database instance type."
  }
}

variable "mongodb_cluster_instances" {
  type        = number
  default     = 3
  description = "MongoDB cluster instances to use for the database cluster."
  validation {
    condition     = var.mongodb_cluster_instances >= 1 && var.mongodb_cluster_instances <= 10
    error_message = "MongoDB cluster instances must be between 1 and 10."
  }
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

variable "additional_prometheus_alerts" {
  type        = string
  default     = ""
  description = "Additional Prometheus alerts to add to the cluster."
  validation {
    condition     = length(trimspace(var.additional_prometheus_alerts)) == 0 || can(yamldecode(var.additional_prometheus_alerts))
    error_message = "The additional_prometheus_alerts provided was invalid."
  }
}

variable "alertmanager_config" {
  type        = string
  default     = "{}"
  description = "Alert Manager configuration as a YAML-encoded string"
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

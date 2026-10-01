variable "upcloud_token" {
  type        = string
  default     = null
  sensitive   = true
  description = "UpCloud API token. Null uses the UPCLOUD_TOKEN environment variable. Cluster Autoscaler stores this value unless upcloud_autoscaler_token is set."
}

variable "upcloud_autoscaler_token" {
  type        = string
  default     = null
  sensitive   = true
  description = "UpCloud API token used only by Cluster Autoscaler. Null uses upcloud_token. Prefer a token that can manage only this cluster.The autoscaler does not read UPCLOUD_TOKEN."
}

variable "zone" {
  type        = string
  default     = "{{ cookiecutter.cloud_region }}"
  description = "UpCloud zone for the private network, UKS cluster, and MySQL. This is not the object storage region."

  validation {
    condition = contains([
      "au-syd1",
      "de-fra1",
      "dk-cph1",
      "es-mad1",
      "fi-hel1",
      "fi-hel2",
      "nl-ams1",
      "pl-waw1",
      "no-svg1",
      "se-sto1",
      "sg-sin1",
      "uk-lon1",
      "us-chi1",
      "us-nyc1",
      "us-sjo1",
    ], var.zone)
    error_message = "The UpCloud zone must be in the acceptable zone list."
  }
}

variable "object_storage_region" {
  type        = string
  default     = null
  description = "Managed Object Storage region. Null uses us-1 for us-nyc1, us-chi1, and us-sjo1, apac-1 for au-syd1 and sg-sin1, and europe-1 for every European zone. Set europe-2 or europe-3 to override that European default."

  validation {
    condition = var.object_storage_region == null || contains([
      "us-1",
      "europe-1",
      "europe-2",
      "europe-3",
      "apac-1",
    ], var.object_storage_region)
    error_message = "object_storage_region must be us-1, europe-1, europe-2, europe-3, or apac-1. de-fra1 is a zone; its object storage region is europe-1."
  }
}

variable "network_cidr" {
  type        = string
  default     = "10.0.0.0/24"
  description = "IPv4 CIDR of the single SDN subnet. UpCloud allows one ip_network per network."

  validation {
    condition     = can(cidrhost(var.network_cidr, 0))
    error_message = "The network CIDR must be a valid CIDR block."
  }
}

variable "gateway_plan" {
  type        = string
  default     = "development"
  description = "NAT gateway plan. List plans with `upctl gateway plans`."
}

variable "kubernetes_cluster_name" {
  type        = string
  default     = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"
  description = "Name prefix of the Kubernetes cluster. The UKS module appends the environment."
}

variable "kubernetes_version" {
  type        = string
  default     = "1.35"
  description = "Kubernetes minor version. List supported versions with `upctl kubernetes versions`."
}

variable "kubernetes_plan" {
  type        = string
  default     = "dev-md"
  description = "UKS control plane plan. List plans with `upctl kubernetes plans`."
}

variable "worker_node_plan" {
  type        = string
  default     = "2xCPU-4GB"
  description = "Server plan for the default worker node group. List plans with `upctl server plans`."
}

variable "worker_node_count" {
  type        = number
  default     = 3
  description = "Initial number of nodes in the default worker group. Cluster Autoscaler may change this later between worker_node_min_count and worker_node_max_count."

  validation {
    condition     = var.worker_node_count >= var.worker_node_min_count && var.worker_node_count <= var.worker_node_max_count
    error_message = "Initial worker node count must sit between worker_node_min_count and worker_node_max_count."
  }
}

variable "worker_node_min_count" {
  type        = number
  default     = 1
  description = "Minimum size Cluster Autoscaler may apply to the workers group. Must be at least 1."

  validation {
    condition     = var.worker_node_min_count >= 1
    error_message = "Worker node minimum must be at least 1. A zero-sized group stops the UpCloud autoscaler."
  }
}

variable "worker_node_max_count" {
  type        = number
  default     = 5
  description = "Maximum size Cluster Autoscaler may apply to the workers group."

  validation {
    condition     = var.worker_node_max_count >= var.worker_node_min_count
    error_message = "Worker node maximum must be at least worker_node_min_count."
  }
}

variable "kubernetes_resource_quotas" {
  type        = string
  default     = "{}"
  description = "Resource configuration for the cluster."

  validation {
    condition     = can(yamldecode(var.kubernetes_resource_quotas))
    error_message = "The kubernetes_resource_quotas provided was invalid."
  }
}

variable "mysql_plan" {
  type        = string
  default     = "1x1xCPU-2GB-25GB"
  description = "Managed MySQL plan. List plans with `upctl database plans mysql`."
}

variable "atlas_project_id" {
  type        = string
  description = "MongoDB Atlas project that hosts the cluster."
}

variable "atlas_region_name" {
  type        = string
  description = "Atlas region for the cluster, for example US_EAST_1 when the UpCloud zone is us-nyc1, or EU_CENTRAL_1 when the zone is de-fra1. This is an Atlas region, not an UpCloud zone."

  validation {
    condition     = length(trimspace(var.atlas_region_name)) > 0
    error_message = "atlas_region_name is required."
  }
}

variable "atlas_public_key" {
  type        = string
  default     = null
  sensitive   = true
  description = "MongoDB Atlas public API key. Null uses the MONGODB_ATLAS_PUBLIC_KEY environment variable."
}

variable "atlas_private_key" {
  type        = string
  default     = null
  sensitive   = true
  description = "MongoDB Atlas private API key. Null uses the MONGODB_ATLAS_PRIVATE_KEY environment variable."
}

variable "lets_encrypt_notification_inbox" {
  type        = string
  default     = "dev@cluster.domain"
  description = "The email address to receive notifications from Let's Encrypt."
}

variable "velero_enabled" {
  type        = bool
  description = "Whether to enable Velero backup."
  default     = false
}

variable "velero_schedules" {
  type        = string
  description = "The schedules for Velero backups."
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
  description = "Alert Manager configuration as a YAML-encoded string."

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

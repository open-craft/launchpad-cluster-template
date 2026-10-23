variable "upcloud_token" {
  type        = string
  default     = null
  sensitive   = true
  description = "UpCloud API token. Null uses the UPCLOUD_TOKEN environment variable."
}

variable "upcloud_autoscaler_token" {
  type        = string
  sensitive   = true
  description = "UpCloud API token used only by Cluster Autoscaler."
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

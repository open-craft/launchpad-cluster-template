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

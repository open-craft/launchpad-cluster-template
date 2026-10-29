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

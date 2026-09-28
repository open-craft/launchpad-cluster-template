output "kubeconfig_content" {
  description = "Kubernetes configuration content for cluster access"
  value       = module.kubernetes_cluster.kubeconfig
  sensitive   = true
}

output "cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = module.kubernetes_cluster.cluster_endpoint
}

output "cluster_name" {
  description = "Kubernetes cluster name"
  value       = module.kubernetes_cluster.cluster_name
}

output "velero_backups_bucket" {
  description = "Velero backups bucket"
  value       = module.velero_backups.bucket_name
}

output "object_storage_endpoint_hostname" {
  description = "Public S3 hostname for Managed Object Storage. Use this as LAUNCHPAD_STORAGE_HOST."
  value       = module.velero_backups.endpoint_hostname
}

output "object_storage_access_key_id" {
  description = "Access key for the Managed Object Storage user."
  value       = module.velero_backups.access_key_id
  sensitive   = true
}

output "object_storage_secret_access_key" {
  description = "Secret key for the Managed Object Storage user."
  value       = module.velero_backups.secret_access_key
  sensitive   = true
}

output "object_storage_region" {
  description = "Managed Object Storage region. Use this as LAUNCHPAD_STORAGE_REGION."
  value       = var.object_storage_region
}

output "mysql_host" {
  description = "MySQL database host"
  value       = module.mysql_database.cluster_host
}

output "mysql_port" {
  description = "MySQL database port"
  value       = module.mysql_database.cluster_port
}

output "mysql_cluster_id" {
  description = "MySQL database cluster ID"
  value       = module.mysql_database.database_cluster_id
}

output "mysql_root_user" {
  description = "MySQL root username"
  value       = module.mysql_database.database_cluster_root_user
  sensitive   = true
}

output "mysql_root_password" {
  description = "MySQL root password"
  value       = module.mysql_database.database_cluster_root_password
  sensitive   = true
}

output "mongodb_host" {
  description = "MongoDB Atlas SRV address. Set this as LAUNCHPAD_MONGODB_HOST."
  value       = module.mongodb_database.atlas_srv_address
}

output "atlas_cluster_name" {
  description = "MongoDB Atlas cluster name. Set this as LAUNCHPAD_ATLAS_CLUSTER_NAME."
  value       = module.mongodb_database.atlas_cluster_name
}

output "atlas_project_id" {
  description = "MongoDB Atlas project ID. Set this as LAUNCHPAD_ATLAS_PROJECT_ID."
  value       = var.atlas_project_id
}

output "grafana_admin_password" {
  description = "Grafana admin password"
  value       = module.harmony.grafana_admin_password
  sensitive   = true
}

output "elasticsearch_ca_cert" {
  description = "Elasticsearch CA certificate"
  value       = module.harmony.elasticsearch_ca_cert
  sensitive   = true
}

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

output "mysql_host" {
  description = "MySQL database host"
  value       = module.mysql_database.cluster_host
}

output "mysql_port" {
  description = "MySQL database port"
  value       = module.mysql_database.cluster_port
}

output "mysql_root_user" {
  description = "MySQL root username"
  value       = module.mysql_database.cluster_root_user
}

output "mysql_root_password" {
  description = "MySQL root password"
  value       = module.mysql_database.cluster_root_password
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

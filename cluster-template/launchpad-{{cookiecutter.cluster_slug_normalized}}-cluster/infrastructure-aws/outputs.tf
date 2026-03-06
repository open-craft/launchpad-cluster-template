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

output "mongodb_address" {
  description = "MongoDB database address"
  value       = module.mongodb_database.cluster_address
}

output "mongodb_connection_string" {
  description = "MongoDB database connection string"
  value       = module.mongodb_database.cluster_connection_strings[0].standard_srv
}

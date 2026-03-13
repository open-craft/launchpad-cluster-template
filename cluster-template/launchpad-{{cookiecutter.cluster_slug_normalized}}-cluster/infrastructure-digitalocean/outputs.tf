output "kubeconfig_content" {
  description = "Kubernetes configuration content for cluster access"
  value       = data.digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config
  sensitive   = true
}

output "cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = data.digitalocean_kubernetes_cluster.cluster.endpoint
}

output "cluster_name" {
  description = "Kubernetes cluster name"
  value       = data.digitalocean_kubernetes_cluster.cluster.name
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
  sensitive   = true
}

output "mysql_root_password" {
  description = "MySQL root password"
  value       = module.mysql_database.cluster_root_password
  sensitive   = true
}

output "mongodb_host" {
  description = "MongoDB database host"
  value       = module.mongodb_database.cluster_host
}

output "mongodb_port" {
  description = "MongoDB database port"
  value       = module.mongodb_database.cluster_port
}

output "mongodb_admin_user" {
  description = "MongoDB admin username"
  value       = module.mongodb_database.cluster_root_user
  sensitive   = true
}

output "mongodb_admin_password" {
  description = "MongoDB admin password"
  value       = module.mongodb_database.cluster_root_password
  sensitive   = true
}

output "grafana_admin_password" {
  value     = module.harmony.grafana_admin_password
  sensitive = true
}

output "openfaas_admin_password" {
  value     = module.harmony.openfaas_admin_password
  sensitive = true
}

output "elasticsearch_ca_cert" {
  value     = module.harmony.elasticsearch_ca_cert
  sensitive = true
}

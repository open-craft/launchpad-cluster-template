module "network" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/network?ref=${local.harmony_terraform_module_version}"

  zone        = local.zone
  environment = local.kubernetes_cluster_environment

  ip_network_address = local.network_cidr
  gateway_plan       = local.gateway_plan
  labels             = local.labels
}

module "kubernetes_cluster" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/uks?ref=${local.harmony_terraform_module_version}"

  zone        = local.zone
  environment = local.kubernetes_cluster_environment

  network_id            = module.network.network_id
  cluster_name          = local.kubernetes_cluster_name
  kubernetes_version    = local.kubernetes_version
  plan                  = local.kubernetes_plan
  worker_node_plan      = local.worker_node_plan
  worker_node_count     = local.worker_node_count
  worker_node_min_count = local.worker_node_min_count
  worker_node_max_count = local.worker_node_max_count
  labels                = local.labels
}

module "cluster_autoscaler" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/uks/autoscaler?ref=${local.harmony_terraform_module_version}"

  cluster_id    = module.kubernetes_cluster.cluster_id
  upcloud_token = var.upcloud_autoscaler_token
  node_groups   = module.kubernetes_cluster.node_groups
}

module "mysql_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/mysql?ref=${local.harmony_terraform_module_version}"

  zone        = local.zone
  environment = local.kubernetes_cluster_environment

  network_id            = module.network.network_id
  network_cidr          = module.network.network_cidr
  database_cluster_name = "${module.kubernetes_cluster.cluster_name}-mysql"
  plan                  = local.mysql_plan
  labels                = local.labels
}

module "mongodb_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/mongodb?ref=${local.harmony_terraform_module_version}"

  environment              = local.kubernetes_cluster_environment
  database_cluster_name    = "${local.kubernetes_cluster_name}-mongodb"
  atlas_project_id         = local.atlas_project_id
  atlas_region_name        = local.atlas_region_name
  atlas_provider_name      = "AWS"
  database_cluster_version = local.mongodb_version
  ip_access_cidrs          = local.atlas_ip_access_cidrs
}

module "velero_backups" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/object-storage?ref=${local.harmony_terraform_module_version}"

  region      = local.object_storage_region
  environment = local.kubernetes_cluster_environment

  bucket_prefix = "backup-${local.kubernetes_cluster_name}"
  network_id    = module.network.network_id
  labels        = local.labels
}

module "harmony" {
  depends_on = [module.kubernetes_cluster]

  source = "git::https://gitlab.com/opencraft/ops/terraform-modules.git//modules/harmony?ref=${local.opencraft_terraform_module_version}"

  cluster_id                      = module.kubernetes_cluster.cluster_id
  cluster_domain                  = local.kubernetes_cluster_domain
  cluster_provider                = "upcloud"
  lets_encrypt_notification_inbox = local.lets_encrypt_notification_inbox
  ingress_resource_quota          = lookup(yamldecode(local.kubernetes_resource_quotas), "traefik", {})
  prometheus_enabled              = local.prometheus_enabled
  prometheus_additional_alerts    = local.additional_prometheus_alerts
  grafana_enabled                 = local.grafana_enabled
  grafana_host                    = "grafana.${local.kubernetes_cluster_domain}"
  alertmanager_enabled            = local.prometheus_enabled
  alertmanager_config             = local.alertmanager_config
  velero_enabled                  = local.velero_enabled
  velero_backup_bucket            = module.velero_backups.bucket_name
  velero_backup_region            = local.object_storage_region
  velero_backup_s3_url            = "https://${module.velero_backups.endpoint_hostname}"
  velero_backup_access_key_id     = module.velero_backups.access_key_id
  velero_backup_secret_access_key = module.velero_backups.secret_access_key
  velero_plugin_aws_version       = local.velero_aws_plugin_tag
  velero_schedules                = local.velero_schedules
}

resource "local_sensitive_file" "kubeconfig" {
  filename        = "${path.module}/.kubeconfig"
  content         = module.kubernetes_cluster.kubeconfig
  file_permission = "0400"
}

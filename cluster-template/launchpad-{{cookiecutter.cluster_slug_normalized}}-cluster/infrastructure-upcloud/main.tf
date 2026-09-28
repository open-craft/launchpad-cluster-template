locals {
  context_file = jsondecode(file("${path.module}/../context.json"))

  # Kubernetes cluster environment
  kubernetes_cluster_domain      = local.context_file.cluster_domain
  kubernetes_cluster_environment = local.context_file.environment

  harmony_terraform_module_version   = "{{ cookiecutter.harmony_module_version }}"
  opencraft_terraform_module_version = "{{ cookiecutter.opencraft_module_version }}"

  # https://github.com/vmware-tanzu/velero-plugin-for-aws/releases
  velero_aws_plugin_tag = "v1.9.0"

  atlas_region_name     = var.atlas_region_name
  atlas_ip_access_cidrs = ["${module.network.gateway_public_ip}/32"]

  labels = {
    environment = local.kubernetes_cluster_environment
    project     = "launchpad"
  }
}

module "network" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/network?ref=${local.harmony_terraform_module_version}"

  zone        = var.zone
  environment = local.kubernetes_cluster_environment

  ip_network_address = var.network_cidr
  gateway_plan       = var.gateway_plan
  labels             = local.labels
}

module "kubernetes_cluster" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/uks?ref=${local.harmony_terraform_module_version}"

  zone        = var.zone
  environment = local.kubernetes_cluster_environment

  network_id            = module.network.network_id
  cluster_name          = var.kubernetes_cluster_name
  kubernetes_version    = var.kubernetes_version
  plan                  = var.kubernetes_plan
  worker_node_plan      = var.worker_node_plan
  worker_node_count     = var.worker_node_count
  worker_node_min_count = var.worker_node_min_count
  worker_node_max_count = var.worker_node_max_count
  labels                = local.labels
}

module "cluster_autoscaler" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/uks/autoscaler?ref=${local.harmony_terraform_module_version}"

  cluster_id    = module.kubernetes_cluster.cluster_id
  upcloud_token = coalesce(var.upcloud_autoscaler_token, var.upcloud_token)
  node_groups   = module.kubernetes_cluster.node_groups
}

module "mysql_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/mysql?ref=${local.harmony_terraform_module_version}"

  zone        = var.zone
  environment = local.kubernetes_cluster_environment

  network_id            = module.network.network_id
  network_cidr          = module.network.network_cidr
  database_cluster_name = "${module.kubernetes_cluster.cluster_name}-mysql"
  plan                  = var.mysql_plan
  labels                = local.labels
}

module "mongodb_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/mongodb?ref=${local.harmony_terraform_module_version}"

  environment           = local.kubernetes_cluster_environment
  database_cluster_name = "${var.kubernetes_cluster_name}-mongodb"
  atlas_project_id      = var.atlas_project_id
  atlas_region_name     = local.atlas_region_name
  atlas_provider_name   = "AWS"
  ip_access_cidrs       = local.atlas_ip_access_cidrs
}

module "velero_backups" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/upcloud/object-storage?ref=${local.harmony_terraform_module_version}"

  region      = var.object_storage_region
  environment = local.kubernetes_cluster_environment

  bucket_prefix = "backup-${var.kubernetes_cluster_name}"
  network_id    = module.network.network_id
  labels        = local.labels
}

module "harmony" {
  depends_on = [module.kubernetes_cluster]

  source = "git::https://gitlab.com/opencraft/ops/terraform-modules.git//modules/harmony?ref=${local.opencraft_terraform_module_version}"

  cluster_id                      = module.kubernetes_cluster.cluster_id
  cluster_domain                  = local.kubernetes_cluster_domain
  cluster_provider                = "upcloud"
  lets_encrypt_notification_inbox = var.lets_encrypt_notification_inbox
  ingress_resource_quota          = lookup(yamldecode(var.kubernetes_resource_quotas), "nginx", {})
  prometheus_enabled              = var.prometheus_enabled
  prometheus_additional_alerts    = var.additional_prometheus_alerts
  grafana_enabled                 = var.grafana_enabled
  grafana_host                    = "grafana.${local.kubernetes_cluster_domain}"
  alertmanager_enabled            = var.prometheus_enabled
  alertmanager_config             = var.alertmanager_config
  velero_enabled                  = var.velero_enabled
  velero_backup_bucket            = module.velero_backups.bucket_name
  velero_backup_region            = var.object_storage_region
  velero_backup_s3_url            = "https://${module.velero_backups.endpoint_hostname}"
  velero_backup_access_key_id     = module.velero_backups.access_key_id
  velero_backup_secret_access_key = module.velero_backups.secret_access_key
  velero_plugin_aws_version       = local.velero_aws_plugin_tag
  velero_schedules                = var.velero_schedules
}

resource "local_sensitive_file" "kubeconfig" {
  filename        = "${path.module}/.kubeconfig"
  content         = module.kubernetes_cluster.kubeconfig
  file_permission = "0400"
}

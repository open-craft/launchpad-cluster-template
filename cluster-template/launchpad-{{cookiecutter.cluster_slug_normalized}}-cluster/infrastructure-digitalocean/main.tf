locals {
  context_file = jsondecode(file("${path.module}/../context.json"))

  # Kubernetes cluster nodes
  kubernetes_worker_node_size       = "m-4vcpu-32gb"
  kubernetes_cluster_min_node_count = 3
  kubernetes_cluster_max_node_count = 5

  # Kubernetes cluster environment
  kubernetes_cluster_domain      = local.context_file.cluster_domain
  kubernetes_cluster_environment = local.context_file.environment

  harmony_terraform_module_version   = "{{ cookiecutter.harmony_module_version }}"
  opencraft_terraform_module_version = "{{ cookiecutter.opencraft_module_version }}"

  # Velero plugin versions
  velero_aws_plugin_tag          = "v1.9.0" # https://github.com/vmware-tanzu/velero-plugin-for-aws/releases
  velero_digitalocean_plugin_tag = "v1.1.0" # https://github.com/digitalocean/velero-plugin/releases

  # MySQL
  mysql_version           = "8"
  mysql_instance_size     = "db-s-1vcpu-2gb"
  mysql_cluster_instances = 2

  # MongoDB
  mongodb_version           = "7"
  mongodb_instance_size     = "db-s-4vcpu-8gb"
  mongodb_cluster_instances = 1
}

module "main_vpc" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/vpc?ref=${local.harmony_terraform_module_version}"

  region      = var.region
  environment = local.kubernetes_cluster_environment

  vpc_ip_range = var.vpc_ip_range
}

module "kubernetes_cluster" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/doks?ref=${local.harmony_terraform_module_version}"

  region      = var.region
  environment = local.kubernetes_cluster_environment
  vpc_id      = module.main_vpc.vpc_id

  cluster_name       = var.kubernetes_cluster_name
  kubernetes_version = var.kubernetes_version

  worker_node_size      = local.kubernetes_worker_node_size
  worker_node_min_count = local.kubernetes_cluster_min_node_count
  worker_node_max_count = local.kubernetes_cluster_max_node_count
}

module "mysql_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/database?ref=${local.harmony_terraform_module_version}"

  region                  = var.region
  environment             = local.kubernetes_cluster_environment
  access_token            = var.access_token
  vpc_id                  = module.main_vpc.vpc_id
  kubernetes_cluster_name = var.kubernetes_cluster_name

  database_engine                  = "mysql"
  database_engine_version          = local.mysql_version
  database_cluster_instances       = local.mysql_cluster_instances
  database_cluster_instance_size   = local.mysql_instance_size
  database_maintenance_window_day  = "sunday"
  database_maintenance_window_time = "01:00:00"

  # Database cluster firewalls cannot use VPC CIDR, therefore the access is
  # limited to the k8s cluster
  firewall_rules = [
    {
      type  = "k8s"
      value = module.kubernetes_cluster.cluster_id
    },
  ]
}

module "mongodb_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/database?ref=${local.harmony_terraform_module_version}"

  region                  = var.region
  environment             = local.kubernetes_cluster_environment
  access_token            = var.access_token
  vpc_id                  = module.main_vpc.vpc_id
  kubernetes_cluster_name = var.kubernetes_cluster_name

  database_engine                  = "mongodb"
  database_engine_version          = local.mongodb_version
  database_cluster_instances       = local.mongodb_cluster_instances
  database_cluster_instance_size   = local.mongodb_instance_size
  database_maintenance_window_day  = "sunday"
  database_maintenance_window_time = "1:00"

  # Database cluster firewalls cannot use VPC CIDR, therefore the access is
  # limited to the k8s cluster
  firewall_rules = [
    {
      type  = "k8s"
      value = module.kubernetes_cluster.cluster_id
    },
  ]
}

module "velero_backups" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/spaces?ref=${local.harmony_terraform_module_version}"

  bucket_prefix = "backup-${var.kubernetes_cluster_name}"
  region        = var.region
  environment   = local.kubernetes_cluster_environment

  is_versioning_enabled    = false
  is_force_destroy_enabled = false
}

module "harmony" {
  depends_on = [module.kubernetes_cluster]

  source = "git::https://gitlab.com/opencraft/ops/terraform-modules.git//modules/harmony?ref=${local.opencraft_terraform_module_version}"

  cluster_id                         = module.kubernetes_cluster.cluster_id
  cluster_domain                     = local.kubernetes_cluster_domain
  cluster_provider                   = "digitalocean"
  lets_encrypt_notification_inbox    = var.lets_encrypt_notification_inbox
  ingress_resource_quota             = lookup(yamldecode(var.kubernetes_resource_quotas), "nginx", {})
  prometheus_enabled                 = var.prometheus_enabled
  prometheus_additional_alerts       = var.additional_prometheus_alerts
  grafana_enabled                    = var.grafana_enabled
  grafana_host                       = "grafana.${local.kubernetes_cluster_domain}"
  alertmanager_enabled               = var.prometheus_enabled
  alertmanager_config                = var.alertmanager_config
  velero_enabled                     = var.velero_enabled
  velero_backup_bucket               = module.velero_backups.bucket_name
  velero_backup_region               = var.region
  velero_backup_access_key_id        = var.access_key_id
  velero_backup_secret_access_key    = var.secret_access_key
  velero_plugin_aws_version          = local.velero_aws_plugin_tag
  velero_plugin_digitalocean_version = local.velero_digitalocean_plugin_tag
  velero_plugin_digitalocean_token   = var.access_token
  velero_volume_snapshot_provider    = "digitalocean.com/velero"
  velero_schedules                   = var.velero_schedules
}

resource "digitalocean_project" "project" {
  name        = var.kubernetes_cluster_name
  description = "{{ cookiecutter.short_description }}"
  purpose     = "Open edX Instance Hosting"

  resources = [
    module.kubernetes_cluster.cluster_urn,
    module.mysql_database.cluster_urn,
    module.mongodb_database.cluster_urn,
  ]
}

resource "local_sensitive_file" "kubeconfig" {
  filename        = "${path.cwd}/.kubeconfig"
  content         = data.digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config
  file_permission = "0400"
}

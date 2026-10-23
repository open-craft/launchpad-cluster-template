module "main_vpc" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/vpc?ref=${local.harmony_terraform_module_version}"

  region      = local.region
  environment = local.kubernetes_cluster_environment

  vpc_ip_range = local.vpc_ip_range
}

module "kubernetes_cluster" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/doks?ref=${local.harmony_terraform_module_version}"

  region      = local.region
  environment = local.kubernetes_cluster_environment
  vpc_id      = module.main_vpc.vpc_id

  cluster_name       = local.kubernetes_cluster_name
  kubernetes_version = local.kubernetes_version

  worker_node_size      = local.worker_node_size
  min_worker_node_count = local.worker_node_min_count
  max_worker_node_count = local.worker_node_max_count
}

module "mysql_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/digitalocean/database?ref=${local.harmony_terraform_module_version}"

  region                  = local.region
  environment             = local.kubernetes_cluster_environment
  access_token            = var.access_token
  vpc_id                  = module.main_vpc.vpc_id
  kubernetes_cluster_name = local.kubernetes_cluster_name

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

  region                  = local.region
  environment             = local.kubernetes_cluster_environment
  access_token            = var.access_token
  vpc_id                  = module.main_vpc.vpc_id
  kubernetes_cluster_name = local.kubernetes_cluster_name

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

  bucket_prefix = "backup-${local.kubernetes_cluster_name}"
  region        = local.region
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
  lets_encrypt_notification_inbox    = local.lets_encrypt_notification_inbox
  ingress_resource_quota             = lookup(yamldecode(local.kubernetes_resource_quotas), "traefik", {})
  prometheus_enabled                 = local.prometheus_enabled
  prometheus_additional_alerts       = local.additional_prometheus_alerts
  grafana_enabled                    = local.grafana_enabled
  grafana_host                       = "grafana.${local.kubernetes_cluster_domain}"
  alertmanager_enabled               = local.prometheus_enabled
  alertmanager_config                = local.alertmanager_config
  velero_enabled                     = local.velero_enabled
  velero_backup_bucket               = module.velero_backups.bucket_name
  velero_backup_region               = local.region
  velero_backup_access_key_id        = var.access_key_id
  velero_backup_secret_access_key    = var.secret_access_key
  velero_plugin_aws_version          = local.velero_aws_plugin_tag
  velero_plugin_digitalocean_version = local.velero_digitalocean_plugin_tag
  velero_plugin_digitalocean_token   = var.access_token
  velero_volume_snapshot_provider    = "digitalocean.com/velero"
  velero_schedules                   = local.velero_schedules
}

resource "digitalocean_project" "project" {
  name        = local.kubernetes_cluster_name
  description = "{{ cookiecutter.short_description }}"
  purpose     = "Open edX Instance Hosting"

  resources = [
    module.kubernetes_cluster.cluster_urn,
    module.mysql_database.cluster_urn,
    module.mongodb_database.cluster_urn,
  ]
}

resource "local_sensitive_file" "kubeconfig" {
  filename        = "${path.module}/.kubeconfig"
  content         = data.digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config
  file_permission = "0400"
}

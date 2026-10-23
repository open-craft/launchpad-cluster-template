locals {
  context_file = jsondecode(file("${path.module}/../context.json"))

  # Kubernetes cluster environment
  kubernetes_cluster_domain      = local.context_file.cluster_domain
  kubernetes_cluster_environment = local.context_file.environment

  harmony_terraform_module_version   = "{{ cookiecutter.harmony_module_version }}"
  opencraft_terraform_module_version = "{{ cookiecutter.opencraft_module_version }}"

  region                  = "{{ cookiecutter.cloud_region }}"
  vpc_cidr                = "10.0.0.0/16"
  private_subnets         = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets          = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  kubernetes_cluster_name = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"

  kubernetes_version         = "1.36"
  ubuntu_version             = "resolute-26.04"
  worker_node_instance_types = ["r7i.xlarge"]
  worker_node_count          = 2
  worker_node_min_count      = 2
  worker_node_max_count      = 8

  mysql_version       = "8.4"
  mysql_instance_size = "db.t4g.small"
  mongodb_version     = "7.0"

  kubernetes_resource_quotas      = "{}"
  lets_encrypt_notification_inbox = "dev@cluster.domain"
  velero_enabled                  = false
  velero_schedules                = "{\"hourly-backup\":{\"disabled\":false,\"schedule\":\"30 */1 * * *\",\"template\":{\"ttl\":\"24h\"}},\"daily-backup\":{\"disabled\":false,\"schedule\":\"0 6 * * *\",\"template\":{\"ttl\":\"168h\"}},\"weekly-backup\":{\"disabled\":false,\"schedule\":\"59 23 * * 0\",\"template\":{\"ttl\":\"720h\"}}}"
  prometheus_enabled              = true
  additional_prometheus_alerts    = ""
  alertmanager_config             = "{}"
  grafana_enabled                 = true

  # https://github.com/vmware-tanzu/velero-plugin-for-aws/releases
  velero_aws_plugin_tag = "v1.14.4"

  # Must not overlap vpc_cidr.
  atlas_cidr_block      = "192.168.248.0/21"
  atlas_project_id      = "atlas-project-id"
  atlas_region_name     = upper(replace(local.region, "-", "_"))
  atlas_ip_access_cidrs = [module.main_vpc.vpc_cidr_block]
}

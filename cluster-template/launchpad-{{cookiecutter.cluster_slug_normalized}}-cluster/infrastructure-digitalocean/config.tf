locals {
  context_file = jsondecode(file("${path.module}/../context.json"))

  # Kubernetes cluster environment
  kubernetes_cluster_domain      = local.context_file.cluster_domain
  kubernetes_cluster_environment = local.context_file.environment

  harmony_terraform_module_version   = "{{ cookiecutter.harmony_module_version }}"
  opencraft_terraform_module_version = "{{ cookiecutter.opencraft_module_version }}"

  region                  = "{{ cookiecutter.cloud_region }}"
  vpc_ip_range            = "10.12.0.0/24"
  kubernetes_cluster_name = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"

  kubernetes_version    = "1.34.1-do.1"
  worker_node_size      = "m-4vcpu-32gb"
  worker_node_min_count = 3
  worker_node_max_count = 5

  mysql_version           = "8"
  mysql_instance_size     = "db-s-1vcpu-2gb"
  mysql_cluster_instances = 2

  mongodb_version           = "7"
  mongodb_instance_size     = "db-s-4vcpu-8gb"
  mongodb_cluster_instances = 1

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

  # https://github.com/digitalocean/velero-plugin/releases
  velero_digitalocean_plugin_tag = "v1.1.0"
}

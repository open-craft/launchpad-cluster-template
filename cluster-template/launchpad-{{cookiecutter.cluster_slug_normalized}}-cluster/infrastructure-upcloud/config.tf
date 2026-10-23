locals {
  context_file = jsondecode(file("${path.module}/../context.json"))

  # Kubernetes cluster environment
  kubernetes_cluster_domain      = local.context_file.cluster_domain
  kubernetes_cluster_environment = local.context_file.environment

  harmony_terraform_module_version   = "{{ cookiecutter.harmony_module_version }}"
  opencraft_terraform_module_version = "{{ cookiecutter.opencraft_module_version }}"

  zone                    = "{{ cookiecutter.cloud_region }}"
  network_cidr            = "10.0.0.0/24"
  gateway_plan            = "development"
  kubernetes_cluster_name = "launchpad-{{ cookiecutter.cluster_slug_normalized }}"

  kubernetes_version    = "1.35"
  kubernetes_plan       = "dev-md"
  worker_node_plan      = "2xCPU-4GB"
  worker_node_count     = 3
  worker_node_min_count = 1
  worker_node_max_count = 5

  mysql_plan      = "1x1xCPU-2GB-25GB"
  mongodb_version = "7.0"

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

  atlas_project_id = "atlas-project-id"
  atlas_region_name_by_zone = {
    "au-syd1" = "AP_SOUTHEAST_2"
    "sg-sin1" = "AP_SOUTHEAST_1"
    "us-chi1" = "US_EAST_1"
    "us-nyc1" = "US_EAST_1"
    "us-sjo1" = "US_EAST_1"
    "de-fra1" = "EU_CENTRAL_1"
    "dk-cph1" = "EU_CENTRAL_1"
    "es-mad1" = "EU_CENTRAL_1"
    "fi-hel1" = "EU_CENTRAL_1"
    "fi-hel2" = "EU_CENTRAL_1"
    "nl-ams1" = "EU_CENTRAL_1"
    "pl-waw1" = "EU_CENTRAL_1"
    "no-svg1" = "EU_CENTRAL_1"
    "se-sto1" = "EU_CENTRAL_1"
    "uk-lon1" = "EU_CENTRAL_1"
  }
  atlas_region_name     = local.atlas_region_name_by_zone[local.zone]
  atlas_ip_access_cidrs = ["${module.network.gateway_public_ip}/32"]

  object_storage_region_by_zone = {
    "au-syd1" = "apac-1"
    "sg-sin1" = "apac-1"
    "us-chi1" = "us-1"
    "us-nyc1" = "us-1"
    "us-sjo1" = "us-1"
    "de-fra1" = "europe-1"
    "dk-cph1" = "europe-1"
    "es-mad1" = "europe-1"
    "fi-hel1" = "europe-1"
    "fi-hel2" = "europe-1"
    "nl-ams1" = "europe-1"
    "pl-waw1" = "europe-1"
    "no-svg1" = "europe-1"
    "se-sto1" = "europe-1"
    "uk-lon1" = "europe-1"
  }

  # Set this to europe-2 or europe-3 to override the zone default. Null uses the map.
  object_storage_region_override = null
  object_storage_region = coalesce(
    local.object_storage_region_override,
    local.object_storage_region_by_zone[local.zone],
  )

  labels = {
    environment = local.kubernetes_cluster_environment
    project     = "launchpad"
  }
}

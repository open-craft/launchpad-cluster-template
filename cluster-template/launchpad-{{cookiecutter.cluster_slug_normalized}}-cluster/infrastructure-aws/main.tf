data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {}

module "main_vpc" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/aws/vpc?ref=${local.harmony_terraform_module_version}"

  environment        = local.kubernetes_cluster_environment
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 3)

  single_nat_gateway     = true
  one_nat_gateway_per_az = false

  cidr            = local.vpc_cidr
  private_subnets = local.private_subnets
  public_subnets  = local.public_subnets

  public_subnet_tags = {
    "Tier"                   = "Public"
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "Tier"                            = "Private"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

module "kubernetes_cluster" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/aws/eks?ref=${local.harmony_terraform_module_version}"

  environment = local.kubernetes_cluster_environment
  vpc_id      = module.main_vpc.vpc_id
  subnet_ids  = module.main_vpc.private_subnets

  cluster_name         = local.kubernetes_cluster_name
  kubernetes_version   = local.kubernetes_version
  ubuntu_version       = local.ubuntu_version
  registry_credentials = "" # Registry credentials are installed outside separately.

  worker_node_instance_types = local.worker_node_instance_types
  worker_node_count          = local.worker_node_count
  min_worker_node_count      = local.worker_node_min_count
  max_worker_node_count      = local.worker_node_max_count
}

resource "kubernetes_storage_class_v1" "gp3" {
  depends_on = [module.kubernetes_cluster]

  metadata {
    name = "gp3"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }

  storage_provisioner    = "ebs.csi.aws.com"
  reclaim_policy         = "Delete"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "gp3"
    fsType    = "ext4"
    encrypted = "true"
  }
}

resource "kubernetes_annotations" "gp2" {
  depends_on = [module.kubernetes_cluster]

  api_version = "storage.k8s.io/v1"
  kind        = "StorageClass"
  force       = true

  metadata {
    name = "gp2"
  }

  annotations = {
    "storageclass.kubernetes.io/is-default-class" = "false"
  }
}

module "velero_backups" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/aws/s3?ref=${local.harmony_terraform_module_version}"

  bucket_prefix = "backup-${local.kubernetes_cluster_name}"
  environment   = local.kubernetes_cluster_environment

  is_versioning_enabled    = false
  is_force_destroy_enabled = false
}

module "harmony" {
  depends_on = [module.kubernetes_cluster]

  source = "git::https://gitlab.com/opencraft/ops/terraform-modules.git//modules/harmony?ref=${local.opencraft_terraform_module_version}"

  cluster_id                      = module.kubernetes_cluster.cluster_name
  cluster_domain                  = local.kubernetes_cluster_domain
  cluster_provider                = "aws"
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
  velero_backup_region            = local.region
  velero_backup_access_key_id     = var.aws_access_key_id
  velero_backup_secret_access_key = var.aws_secret_access_key
  velero_plugin_aws_version       = local.velero_aws_plugin_tag
  velero_volume_snapshot_provider = "aws"
  velero_schedules                = local.velero_schedules
}

module "mysql_database" {
  source     = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/aws/rds?ref=${local.harmony_terraform_module_version}"
  depends_on = [module.main_vpc]

  environment = local.kubernetes_cluster_environment
  vpc_id      = module.main_vpc.vpc_id
  subnet_ids  = module.main_vpc.private_subnets

  database_cluster_name          = "${module.kubernetes_cluster.cluster_name}-mysql"
  database_engine_version        = local.mysql_version
  database_cluster_instance_size = local.mysql_instance_size
}

module "atlas_network" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/aws/atlas-network?ref=${local.harmony_terraform_module_version}"

  region         = local.region
  aws_account_id = data.aws_caller_identity.current.account_id

  atlas_project_id  = local.atlas_project_id
  atlas_region_name = local.atlas_region_name
  atlas_cidr_block  = local.atlas_cidr_block

  vpc_id                  = module.main_vpc.vpc_id
  private_route_table_ids = module.main_vpc.private_route_table_ids
}

module "mongodb_database" {
  source = "git::https://github.com/openedx/openedx-k8s-harmony.git//terraform/modules/mongodb?ref=${local.harmony_terraform_module_version}"

  depends_on = [module.atlas_network]

  environment              = local.kubernetes_cluster_environment
  database_cluster_name    = "${local.kubernetes_cluster_name}-mongodb"
  atlas_project_id         = local.atlas_project_id
  atlas_region_name        = local.atlas_region_name
  atlas_provider_name      = "AWS"
  database_cluster_version = local.mongodb_version
  ip_access_cidrs          = local.atlas_ip_access_cidrs
}

resource "local_sensitive_file" "kubeconfig" {
  filename        = "${path.module}/.kubeconfig"
  content         = local.kubeconfig
  file_permission = "0400"
}

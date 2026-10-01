terraform {
  backend "s3" {
    key = "terraform.tfstate"

    # The public hostname is created with the Managed Object Storage service
    # (https://<service-id>.upcloudobjects.com). It cannot be derived from the
    # zone. Create the state bucket first, then pass the connection in backend.hcl:
    #
    # endpoints  = { s3 = "https://<service-id>.upcloudobjects.com" }
    # bucket     = "tfstate-launchpad-<slug>-cluster-<environment>"
    # region     = "<object storage region, for example us-1>"
    # access_key = "<KEY_ID>"
    # secret_key = "<SECRET_KEY>"
    #
    # tofu init -backend-config=backend.hcl

    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_s3_checksum            = true
    use_path_style              = true
  }

  required_providers {
    upcloud = {
      source  = "UpCloudLtd/upcloud"
      version = ">= 5.44.1"
    }

    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = ">= 2.17.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.38"
    }

    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">= 1.19"
    }

    helm = {
      source  = "hashicorp/helm"
      version = "2.17.0"
    }

    local = {
      source  = "hashicorp/local"
      version = ">= 2.5.0"
    }
  }
}

locals {
  kubeconfig         = yamldecode(module.kubernetes_cluster.kubeconfig)
  kubeconfig_cluster = local.kubeconfig["clusters"][0]["cluster"]
  kubeconfig_user    = local.kubeconfig["users"][0]["user"]
}

provider "upcloud" {
  token = var.upcloud_token
}

provider "mongodbatlas" {
  public_key  = var.atlas_public_key
  private_key = var.atlas_private_key
}

provider "kubernetes" {
  host                   = local.kubeconfig_cluster["server"]
  client_certificate     = base64decode(local.kubeconfig_user["client-certificate-data"])
  client_key             = base64decode(local.kubeconfig_user["client-key-data"])
  cluster_ca_certificate = base64decode(local.kubeconfig_cluster["certificate-authority-data"])
}

provider "helm" {
  kubernetes {
    host                   = local.kubeconfig_cluster["server"]
    client_certificate     = base64decode(local.kubeconfig_user["client-certificate-data"])
    client_key             = base64decode(local.kubeconfig_user["client-key-data"])
    cluster_ca_certificate = base64decode(local.kubeconfig_cluster["certificate-authority-data"])
  }
}

provider "kubectl" {
  host                   = local.kubeconfig_cluster["server"]
  client_certificate     = base64decode(local.kubeconfig_user["client-certificate-data"])
  client_key             = base64decode(local.kubeconfig_user["client-key-data"])
  cluster_ca_certificate = base64decode(local.kubeconfig_cluster["certificate-authority-data"])
  load_config_file       = false
}

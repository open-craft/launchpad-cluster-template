terraform {
  backend "s3" {
    bucket = "tfstate-launchpad-{{ cookiecutter.cluster_slug_normalized }}-cluster-{{ cookiecutter.environment }}"
    key    = "terraform.tfstate"
    region = "{{ cookiecutter.cloud_region }}"

    # Access credentials should be provided via the `backend.hcl`:
    # access_key = "<KEY_ID>"
    # secret_key = "<SECRET_KEY>"
    #
    # `tofu init -backend-config=backend.hcl`
  }

  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.62"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }

    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 2.17"
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
      version = "3.3.0"
    }

    local = {
      source  = "hashicorp/local"
      version = ">= 2.5.0"
    }
  }
}

data "aws_eks_cluster" "cluster" {
  name       = module.kubernetes_cluster.cluster_name
  depends_on = [module.kubernetes_cluster]
}

# Uses the AWS provider credentials. A token lasts about 15 minutes, so a new
# apply refreshes .kubeconfig.
data "aws_eks_cluster_auth" "cluster" {
  name = data.aws_eks_cluster.cluster.name
}

locals {
  # Plain YAML. yamlencode quotes every key, and the Launchpad CLI requires
  # the document to start with "apiVersion:" and contain "kind: Config".
  kubeconfig = <<-EOT
    apiVersion: v1
    kind: Config
    current-context: ${data.aws_eks_cluster.cluster.name}
    clusters:
    - name: ${data.aws_eks_cluster.cluster.name}
      cluster:
        server: ${data.aws_eks_cluster.cluster.endpoint}
        certificate-authority-data: ${data.aws_eks_cluster.cluster.certificate_authority[0].data}
    contexts:
    - name: ${data.aws_eks_cluster.cluster.name}
      context:
        cluster: ${data.aws_eks_cluster.cluster.name}
        user: ${data.aws_eks_cluster.cluster.name}
    users:
    - name: ${data.aws_eks_cluster.cluster.name}
      user:
        token: ${data.aws_eks_cluster_auth.cluster.token}
  EOT
}

provider "aws" {
  region     = local.region
  access_key = var.aws_access_key_id
  secret_key = var.aws_secret_access_key
}

provider "mongodbatlas" {
  public_key  = var.atlas_public_key
  private_key = var.atlas_private_key
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

provider "helm" {
  kubernetes = {
    host                   = data.aws_eks_cluster.cluster.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.cluster.token
  }
}

provider "kubectl" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
  load_config_file       = false
}

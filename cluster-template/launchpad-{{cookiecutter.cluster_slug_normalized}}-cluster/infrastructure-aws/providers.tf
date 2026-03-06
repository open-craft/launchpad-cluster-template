terraform {
  backend "s3" {
    bucket = "tfstate-launchpad-{{ cookiecutter.cluster_slug_normalized }}-cluster-{{ cookiecutter.environment }}"
    key    = "terraform.tfstate"
    region = var.region

    # Access credentials should be provided via via the `backend.hcl`:
    # access_key = "<KEY_ID>"
    # secret_key = "<SECRET_KEY>"
    #
    # `terraform init -backend-config=backend.hcl`
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">=6.16"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">=2.38"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">=1.19"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "2.17.0"
    }
  }
}

provider "aws" {
  region     = var.region
  access_key = var.aws_access_key_id
  secret_key = var.aws_secret_access_key
}

provider "kubernetes" {
  # AWS EKS cluster configuration will be handled by the AWS provider
}

provider "helm" {
  kubernetes {
    # AWS EKS cluster configuration will be handled by the AWS provider
  }
}

provider "kubectl" {
  # AWS EKS cluster configuration will be handled by the AWS provider
  load_config_file = false
}

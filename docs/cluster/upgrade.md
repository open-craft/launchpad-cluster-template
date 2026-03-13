# Cluster Upgrade

This page outlines how to upgrade cluster components in the Launchpad stack.

## Overview

Upgrades may involve:

- **Kubernetes version** -  Managed by the cloud provider (EKS/DOKS)
- **ArgoCD** -  Version is set via `LAUNCHPAD_ARGOCD_VERSION`; re-run or adjust install
- **Argo Workflows** -  Version is set via `LAUNCHPAD_ARGO_WORKFLOWS_VERSION`
- **Node pools** -  Updated via Terraform/OpenTofu (e.g. AMI/image or node version)
- **Harmony / Terraform modules** -  Bump module refs in Terraform and apply

Always review release notes and backup critical state before upgrading.

## ArgoCD and Argo Workflows

To change the version of ArgoCD or Argo Workflows:

1. Set the desired version (e.g. `export LAUNCHPAD_ARGOCD_VERSION="v2.x.x"`).
2. Re-run the install so that manifests point to the new version:
   - `launchpad_install_argo` (or `--argocd-only` / `--workflows-only`).

Manifests are pulled from the configured install URLs; ensure the new version is available there.

## Infrastructure (Terraform/OpenTofu)

To upgrade Harmony or other Terraform modules:

1. Update the module `ref` or version in your cluster’s Terraform code (e.g. in `main.tf` or `variables.tf`).
2. Run `tofu plan` and review changes.
3. Apply with `tofu apply`.

Node pool or Kubernetes version changes may trigger rolling updates; check provider documentation for impact.

## Related Documentation

- [Cluster Overview](index.md) -  Cluster operations
- [Infrastructure Provisioning](../infrastructure/provisioning.md) -  Initial install and env vars
- [Cluster Configuration](configuration.md) -  Cluster-wide settings
- [Backup](backup.md) -  Backup before upgrading

## See Also

- [Infrastructure Overview](../infrastructure/index.md) -  Harmony and Terraform modules
- [Instances Overview](../instances/index.md) -  Instance upgrades
- [User Guides Overview](../user-guides/index.md) -  Task-based guides

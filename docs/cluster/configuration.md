# Cluster Configuration

This page summarizes cluster-wide configuration for the Launchpad stack.

## Launchpad CLI Environment Variables

Required for most Launchpad commands:

- **`LAUNCHPAD_CLUSTER_DOMAIN`** -  Cluster domain (e.g. `prod.cluster.domain`)

Optional, but highly recommended:

- **`LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS`** -  Base64-encoded credentials for private image pulls

Optional:

- **`LAUNCHPAD_ARGO_ADMIN_PASSWORD`** -  Admin password for ArgoCD and Argo Workflows
- **`LAUNCHPAD_ARGOCD_VERSION`** -  ArgoCD version (default: `stable`)
- **`LAUNCHPAD_ARGO_WORKFLOWS_VERSION`** -  Argo Workflows version (default: `stable`)
- **`LAUNCHPAD_OPENCRAFT_MANIFESTS_URL`** -  Base URL for OpenCraft manifests
- **`LAUNCHPAD_DOCKER_REGISTRY`** -  Registry hostname (e.g. `ghcr.io`)
- **`LAUNCHPAD_ARGOCD_GITHUB_SSO_ENABLED`** -  Enable ArgoCD GitHub SSO via Dex (default: `false`)
- **`LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_ID`** -  GitHub OAuth App client ID (required when GitHub SSO is enabled)
- **`LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_SECRET`** -  GitHub OAuth App client secret (required when GitHub SSO is enabled)
- **`LAUNCHPAD_ARGOCD_GITHUB_ORGS`** -  Comma-separated GitHub org slugs allowed to sign in (required when GitHub SSO is enabled)

## Terraform/OpenTofu Variables

Cluster infrastructure is configured via variables in the generated cluster repo (`/infrastructure`). See `variables.tf` in that directory for:

- Cloud provider and region
- Cluster name and domain
- Node pool sizing
- Database and storage settings
- Harmony options (monitoring, Velero, etc.)

Backend credentials are typically provided via environment variables (e.g. `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) rather than in `.tf` files.

## Related Documentation

- [Cluster Overview](index.md) -  Cluster operations
- [Infrastructure Provisioning](../infrastructure/provisioning.md) -  Initial setup and required env vars
- [Infrastructure Overview](../infrastructure/index.md) -  Core components
- [Instance Configuration](../instances/configuration.md) -  Instance-level configuration

## See Also

- [Authentication](authentication.md) -  kubeconfig and user management
- [Upgrade](upgrade.md) -  Upgrading components
- [Cluster Monitoring](monitoring.md) -  Prometheus and Grafana config

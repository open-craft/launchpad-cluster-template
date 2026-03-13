# Instances Overview

Open edX instances run in dedicated Kubernetes namespaces and are managed via ArgoCD and Tutor-generated manifests. Each instance has its own configuration, databases, and storage.

## Topics

- **[Provisioning](provisioning.md)** -  Creating a new instance (databases, storage, namespace, ArgoCD application)
- **[Deprovisioning](deprovisioning.md)** -  Deleting an instance and cleaning up resources
- **[Configuration](configuration.md)** -  Instance config files (e.g. `config.yml`), Tutor settings, and secrets
- **[Docker Images](docker-images.md)** -  Building and publishing images with Picasso
- **[Auto-scaling](auto-scaling.md)** -  Scaling instance workloads
- **[Tracking Logs](tracking-logs.md)** -  Accessing and following instance logs
- **[Logging](logging.md)** -  Log aggregation and storage
- **[Monitoring](monitoring.md)** -  Metrics and health checks for instances
- **[Debugging](debugging.md)** -  Common issues and troubleshooting

## Lifecycle

1. **Create** -  `launchpad_create_instance` or GitHub Actions “Create Instance” workflow
2. **Build** -  Trigger image builds (e.g. openedx, MFE) via Picasso/GitHub Actions
3. **Deploy** -  ArgoCD syncs the instance application from the cluster repo
4. **Operate** -  Configure, scale, monitor, and debug as needed
5. **Delete** -  `launchpad_delete_instance` or “Delete Instance” workflow when the instance is no longer needed

## Related Documentation

- [Introduction](../index.md) -  Documentation home
- [Infrastructure Overview](../infrastructure/index.md) -  Cluster components (ArgoCD, Argo Workflows, Tutor, Picasso, Drydock)
- [Provisioning](provisioning.md) -  Creating a new instance
- [Deprovisioning](deprovisioning.md) -  Deleting an instance

## See Also

- [Configuration](configuration.md) -  Instance config and manifests
- [Docker Images](docker-images.md) -  Building images with Picasso
- [Cluster Overview](../cluster/index.md) -  Cluster operations
- [User Guides Overview](../user-guides/index.md) -  Task-based guides

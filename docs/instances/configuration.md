# Instance Configuration

Instance behavior is controlled by configuration files in the cluster repository and by Tutor-generated Kubernetes manifests.

## Configuration Files

Each instance has a directory under `instances/<instance-name>/` in the cluster repo, typically containing:

* **`config.yml`** -  Tutor/Open edX configuration. Used by Tutor to generate Kubernetes manifests and by Picasso for image builds. Contains settings for: Docker images and registry; Tutor version and plugins (e.g. Drydock); Open edX version and repository; LMS/CMS hosts and HTTPS; MySQL, MongoDB, and storage connection details
* **`application.yml`** -  ArgoCD Application manifest that points ArgoCD at the source (e.g. cluster repo path) for this instance.

Picasso may overwrite parts of `config.yml` (e.g. image tags) when building images; avoid hand-editing those sections if you use automated builds.

## Tutor and Drydock

- **Tutor** generates the Kubernetes YAML for the instance (Deployments, Services, Ingress, etc.) from `config.yml`.
- **Drydock** is a Tutor plugin used in this stack; options such as `DRYDOCK_INIT_JOBS` and `DRYDOCK_REGISTRY_CREDENTIALS` are set in `config.yml`.

Regenerate manifests with Tutor from the instance config and commit the result to the cluster repo so ArgoCD can sync.

## Secrets and Sensitive Data

Database passwords and similar values will be:

- Generated at instance creation (e.g. stored in `config.yml`)
- Injected via environment variables in CI (e.g. GitHub Actions secrets) when running `launchpad_create_instance`

Keep `config.yml` and any files containing secrets in a private repository and restrict access.

## Related Documentation

- [Instances Overview](index.md) -  Instance lifecycle
- [Provisioning](provisioning.md) -  How instance config is generated at creation
- [Infrastructure Overview](../infrastructure/index.md) -  Tutor and Drydock
- [Docker Images](docker-images.md) -  How config affects image builds

## See Also

- [Deprovisioning](deprovisioning.md) -  Cleanup and config
- [Debugging](debugging.md) -  Config and secrets troubleshooting
- [Cluster Configuration](../cluster/configuration.md) -  Cluster-wide settings

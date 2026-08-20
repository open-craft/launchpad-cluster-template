# Instance Configuration

Instance behavior is controlled by configuration files in the cluster repository and by Tutor-generated Kubernetes manifests.

## Configuration Files

Each instance has a directory under `instances/<instance-name>/` in the cluster repo, typically containing:

* **`config.yml`** -  Tutor/Open edX configuration. Used by Tutor to generate Kubernetes manifests and by Picasso for image builds. Contains settings for: Docker images and registry; Tutor version and plugins (e.g. Drydock, S3); Open edX version and repository; LMS/CMS hosts and HTTPS; MySQL, MongoDB, and object storage (`S3_*` / `OPENEDX_AWS_*`)
* **`application.yml`** -  ArgoCD Application manifest that points ArgoCD at the source (e.g. cluster repo path) for this instance.

Picasso may overwrite parts of `config.yml` (e.g. image tags) when building images; avoid hand-editing those sections if you use automated builds.

## Tutor and Drydock

- **Tutor** generates the Kubernetes YAML for the instance (Deployments, Services, Ingress, etc.) from `config.yml`.
- **Drydock** is a Tutor plugin used in this stack; options such as `DRYDOCK_INIT_JOBS` and `DRYDOCK_REGISTRY_CREDENTIALS` are set in `config.yml`.

Regenerate manifests with Tutor from the instance config and commit the result to the cluster repo so ArgoCD can sync.

## Object Storage

New instances use [tutor-contrib-s3](https://github.com/cleura/tutor-contrib-s3) settings as the single storage config surface. The same keys configure Open edX uploads and Launchpad’s bucket create/delete workflows.

### Tutor keys in `config.yml`

At instance creation, cluster secrets seed:

| Key | Purpose |
| --- | --- |
| `OPENEDX_AWS_ACCESS_KEY` / `OPENEDX_AWS_SECRET_ACCESS_KEY` | Credentials (from `LAUNCHPAD_STORAGE_ACCESS_KEY_ID` / `LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY`) |
| `S3_STORAGE_BUCKET` | Generated bucket name |
| `S3_REGION` | From `LAUNCHPAD_STORAGE_REGION` |
| `S3_HOST` | Empty for AWS; `{region}.digitaloceanspaces.com` when `LAUNCHPAD_STORAGE_TYPE=spaces` |
| `S3_USE_SSL` | `true` by default |

The instance template installs and enables the `s3` plugin via `PICASSO_EXTRA_COMMANDS`.

### How Launchpad derives provider and endpoint

Bucket workflows still need a provider flag and optional endpoint URL. Tooling derives them from the Tutor keys:

- If `S3_HOST` contains `digitaloceanspaces.com`, the provider is DigitalOcean Spaces (`spaces`), and the endpoint is built from `S3_HOST` / `S3_PORT` / `S3_USE_SSL`.
- Otherwise the provider is AWS (`s3`). An empty `S3_HOST` uses AWS default endpoints (no custom endpoint URL).

Versioning and other AWS-specific bucket options follow that derived provider (enabled for AWS, skipped for Spaces).

### Cluster secrets

`LAUNCHPAD_STORAGE_TYPE`, `LAUNCHPAD_STORAGE_REGION`, and the access key pair remain GitHub Actions / CLI inputs. They seed `config.yml` at create time and can still supply credentials to create/delete if keys are missing from the instance file. They are not a second schema operators must keep in sync inside `config.yml`.

## Secrets and Sensitive Data

Database passwords and similar values will be:

- Generated at instance creation (e.g. stored in `config.yml`)
- Injected via environment variables in CI (e.g. GitHub Actions secrets) when running `launchpad_create_instance`

Storage access keys are written into `OPENEDX_AWS_*` in `config.yml` at create time (same pattern as database passwords). Keep `config.yml` and any files containing secrets in a private repository and restrict access.

## Related Documentation

- [Instances Overview](index.md) -  Instance lifecycle
- [Provisioning](provisioning.md) -  How instance config is generated at creation
- [Cluster Repository Setup](../infrastructure/cluster-repository-setup.md) -  `LAUNCHPAD_STORAGE_*` secrets
- [Infrastructure Overview](../infrastructure/index.md) -  Tutor and Drydock
- [Docker Images](docker-images.md) -  How config affects image builds

## See Also

- [Deprovisioning](deprovisioning.md) -  Cleanup and config
- [Debugging](debugging.md) -  Config and secrets troubleshooting
- [Cluster Configuration](../cluster/configuration.md) -  Cluster-wide settings

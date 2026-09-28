# Cluster Repository Setup

After generating your cluster configuration with `launchpad_create_cluster` and deploying the infrastructure, you need to configure the cluster repository for GitHub Actions and ArgoCD. This guide walks through secrets, environment variables, workflows, and ArgoCD repository connection.

## Overview

The cluster repository contains:

- Terraform infrastructure code
- Instance configurations (`instances/<name>/`)
- GitHub Actions workflows for instance lifecycle and image builds

To use these workflows and allow ArgoCD to sync from the repository, you must:

1. Push the repository to GitHub
2. Configure GitHub Actions secrets
3. Set up the ArgoCD project and connect the repository

## Pushing the Repository to GitHub

The `launchpad_create_cluster` command initializes a git repository and adds a remote. Complete the setup:

1. Create an empty repository in your GitHub organization (e.g. `your-org/launchpad-production-cluster`).

2. Push the cluster repository:

   ```bash
   cd launchpad-production-cluster
   git push -u origin main
   ```

## Configuring GitHub Actions Secrets

Workflows read sensitive values from **repository secrets**. Configure them before running Create Instance, Build, or Delete Instance workflows.

### Where to Add Secrets

1. Open your cluster repository on GitHub.
2. Go to **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Enter the **Name** and **Value** for each secret.

### Required Secrets

| Secret                            | Required for                                                        | Description                                                           |
| --------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `TERRAFORM_SECRETS`               | Create Instance, Delete Instance                                    | HCL content for `secrets.auto.tfvars` (see below)                     |
| `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS` | Create Instance                                                     | Base64-encoded `username:token` for pulling images                    |
| `LAUNCHPAD_MYSQL_HOST`                  | Create Instance, Delete Instance                                    | MySQL server hostname                                                 |
| `LAUNCHPAD_MYSQL_PORT`                  | Create Instance, Delete Instance                                    | MySQL port (default: `3306`)                                          |
| `LAUNCHPAD_MYSQL_ROOT_USER`             | Create Instance, Delete Instance                                    | MySQL admin username                                                  |
| `LAUNCHPAD_MYSQL_ROOT_PASSWORD`         | Create Instance, Delete Instance                                    | MySQL admin password                                                  |
| `LAUNCHPAD_MYSQL_PROVIDER`              | Delete Instance                                                     | MySQL deprovision provider: `direct_sql` or `digitalocean_api`       |
| `LAUNCHPAD_MYSQL_CLUSTER_ID`            | Delete Instance                                                     | DigitalOcean MySQL cluster UUID (required when provider is `digitalocean_api`) |
| `LAUNCHPAD_MONGODB_HOST`                | Create Instance, Delete Instance                                    | MongoDB hostname. On AWS and UpCloud, the Atlas SRV address from output `mongodb_host`. |
| `LAUNCHPAD_MONGODB_PORT`                | Create Instance, Delete Instance                                    | MongoDB port (default: `27017`)                                       |
| `LAUNCHPAD_MONGODB_PROVIDER`            | Create Instance, Delete Instance                                    | `digitalocean_api` or `atlas`                                         |
| `LAUNCHPAD_MONGODB_CLUSTER_ID`          | Create Instance, Delete Instance                                    | DigitalOcean MongoDB cluster ID. Required only when `LAUNCHPAD_MONGODB_PROVIDER=digitalocean_api`. |
| `LAUNCHPAD_MONGODB_REPLICA_SET`         | Create Instance, Delete Instance                                    | MongoDB replica set name                                              |
| `LAUNCHPAD_MONGODB_AUTH_SOURCE`         | Create Instance, Delete Instance                                    | MongoDB auth source (default: `admin`)                                 |
| `LAUNCHPAD_DIGITALOCEAN_TOKEN`          | Create Instance, Delete Instance                                    | DigitalOcean API token for provider-managed database cleanup. Leave empty on UpCloud. |
| `LAUNCHPAD_ATLAS_PUBLIC_KEY`            | Create Instance, Delete Instance                                    | Atlas public API key. Required when `LAUNCHPAD_MONGODB_PROVIDER=atlas`. |
| `LAUNCHPAD_ATLAS_PRIVATE_KEY`           | Create Instance, Delete Instance                                    | Atlas private API key. Required when `LAUNCHPAD_MONGODB_PROVIDER=atlas`. |
| `LAUNCHPAD_ATLAS_PROJECT_ID`            | Create Instance, Delete Instance                                    | Atlas project ID. AWS and UpCloud Terraform output `atlas_project_id`. |
| `LAUNCHPAD_ATLAS_CLUSTER_NAME`          | Create Instance, Delete Instance                                    | Atlas cluster name. AWS and UpCloud Terraform output `atlas_cluster_name`. |
| `LAUNCHPAD_STORAGE_TYPE`                | Create Instance, Delete Instance                                    | `s3` or `spaces`. UpCloud uses `s3` with `LAUNCHPAD_STORAGE_HOST`.   |
| `LAUNCHPAD_STORAGE_REGION`              | Create Instance, Delete Instance                                    | Region written to `S3_REGION`. UpCloud uses the object storage region, for example `us-1`, not the zone. |
| `LAUNCHPAD_STORAGE_HOST`                | Create Instance, Delete Instance                                    | Optional S3 hostname. Set to Terraform output `object_storage_endpoint_hostname` for UpCloud. |
| `LAUNCHPAD_STORAGE_ACCESS_KEY_ID`       | Create Instance, Delete Instance                                    | Written to `OPENEDX_AWS_ACCESS_KEY` (also used by bucket workflows)   |
| `LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY`   | Create Instance, Delete Instance                                    | Written to `OPENEDX_AWS_SECRET_ACCESS_KEY`                            |
| `TERRAFORM_BACKEND_CONFIG`              | Create Instance, Delete Instance                                    | Optional `backend.hcl` contents. Required for UpCloud, whose state endpoint is not in the Terraform files. |
| `SSH_PRIVATE_KEY`                 | Create Instance, Build, Build All, Delete Instance, Update Instance | Private SSH key for cloning the cluster repo and private dependencies |

!!! note "Storage secrets seed tutor-contrib-s3 config"
    `LAUNCHPAD_STORAGE_*` populate Tutor `S3_*` / `OPENEDX_AWS_*` keys in the instance `config.yml` at create time. After that, those Tutor keys are the source of truth for Open edX and for bucket create/delete (provider is Spaces when `S3_HOST` contains `digitaloceanspaces.com`). Set `LAUNCHPAD_STORAGE_HOST` to the Managed Object Storage hostname on UpCloud. Bucket workflows use `--endpoint-url` whenever `S3_HOST` is set, and they skip versioning and public-bucket API calls for that endpoint. See [Object Storage](../instances/configuration.md#object-storage).

### TERRAFORM_SECRETS Format

`TERRAFORM_SECRETS` is the exact content that would go in `infrastructure/secrets.auto.tfvars`. The workflow writes it to that file for Terraform/OpenTofu.

**DigitalOcean**:

```hcl
access_token     = "dop_v1_your_digitalocean_token"
access_key_id    = "your_spaces_access_key_id"
secret_access_key = "your_spaces_secret_access_key"
```

**AWS**:

```hcl
aws_access_key_id     = "AKIA..."
aws_secret_access_key = "your_aws_secret_key"
atlas_project_id      = "atlas-project-id"
atlas_cidr_block      = "192.168.248.0/21"
atlas_public_key      = "atlas-public-key"
atlas_private_key     = "atlas-private-key"
```

`atlas_cidr_block` is the Atlas network container and must not overlap the VPC (`10.0.0.0/16` by default). The Atlas region is the AWS region with hyphens replaced by underscores and uppercased, so `us-east-1` becomes `US_EAST_1`. MongoDB uses `LAUNCHPAD_MONGODB_PROVIDER=atlas`. `LAUNCHPAD_MONGODB_HOST` is the Atlas SRV address from output `mongodb_host`. `LAUNCHPAD_ATLAS_CLUSTER_NAME` is output `atlas_cluster_name`, and `LAUNCHPAD_ATLAS_PROJECT_ID` is output `atlas_project_id`.

**UpCloud**:

```hcl
upcloud_token         = "your-upcloud-token"
object_storage_region = "us-1"
atlas_region_name     = "US_EAST_1"
atlas_project_id      = "atlas-project-id"
atlas_public_key      = "atlas-public-key"
atlas_private_key     = "atlas-private-key"
```

`us-1` is the object storage region for zone `us-nyc1`. Use `europe-1` and Atlas region `EU_CENTRAL_1` for zone `de-fra1`. MySQL deprovision uses `LAUNCHPAD_MYSQL_PROVIDER=direct_sql` with the MySQL host, port, and root credentials from Terraform outputs. MongoDB uses `LAUNCHPAD_MONGODB_PROVIDER=atlas`. `LAUNCHPAD_MONGODB_CLUSTER_ID` is only for `digitalocean_api`. `LAUNCHPAD_MONGODB_HOST` is the Atlas SRV address from output `mongodb_host`. `LAUNCHPAD_ATLAS_CLUSTER_NAME` is output `atlas_cluster_name`, and `LAUNCHPAD_ATLAS_PROJECT_ID` is output `atlas_project_id`.

UpCloud `tofu init` in GitHub Actions reads `TERRAFORM_BACKEND_CONFIG`. Store the same `backend.hcl` contents there, including `endpoints.s3`, `bucket`, `region`, `access_key`, and `secret_key`. The state bucket must exist before the first init.

The generated cluster workflows pass `LAUNCHPAD_STORAGE_HOST`, `LAUNCHPAD_ATLAS_*`, and `TERRAFORM_BACKEND_CONFIG` into the reusable workflow. Point those `uses:` refs at a commit of this repository that declares those secrets. `opencraft_module_version` must likewise be a commit of `terraform-modules` that accepts `cluster_provider = "upcloud"` and `velero_backup_s3_url`.

Create the secret by copying the full HCL block (including variable names) and pasting it as the secret value. Do not wrap it in quotes or encode it further.

### Generating Common Secrets

**Docker registry credentials** (for `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS`):

```bash
# GitHub Container Registry
echo -n "github_username:ghp_your_personal_access_token" | base64

# Docker Hub
echo -n "dockerhub_username:dockerhub_token" | base64
```

Use a GitHub PAT with `read:packages` for GHCR.

**SSH private key** (for `SSH_PRIVATE_KEY`):

```bash
# Generate a new deploy key (if you don't have one)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""

# Add deploy_key.pub as a Deploy Key in your repo (Settings -> Deploy keys)
# Paste the contents of deploy_key (private key) as the SSH_PRIVATE_KEY secret
cat deploy_key
```

The same key is used for cloning the cluster repository and any private dependencies (e.g. edx-platform forks, Tutor plugins).

## GitHub Actions Workflows

The cluster repository includes reusable workflows that you trigger manually.

### Workflow Overview

| Workflow             | Trigger                    | Purpose                                                                 |
| -------------------- | -------------------------- | ----------------------------------------------------------------------- |
| **Create Instance**  | Manual (workflow_dispatch) | Creates a new instance: config, provision workflows, ArgoCD Application |
| **Build Image**      | Manual                     | Builds a single service image (openedx or mfe) for an instance          |
| **Build All Images** | Manual                     | Builds both openedx and mfe images for an instance                      |
| **Delete Instance**  | Manual                     | Removes an instance and runs deprovision workflows                      |
| **Update Instance**  | Manual                     | Merges JSON config into an instance's `config.yml`                      |
| **pre-commit**       | On push/PR                 | Runs linting and formatting                                             |

### How to Trigger Workflows

1. Open your cluster repository on GitHub.
2. Go to the **Actions** tab.
3. Select the workflow from the left sidebar (e.g. "Create Instance").
4. Click **Run workflow**.
5. Fill in the inputs and run.

### Common Workflow Inputs

| Input                               | Workflows                                | Description                                                                                                                       |
| ----------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **INSTANCE_NAME**                   | Create, Build, Build All, Delete, Update | Instance identifier (DNS-compliant, e.g. `my-instance`)                                                                           |
| **STRAIN_REPOSITORY_BRANCH**        | Build, Build All                         | Branch to use for the strain (default: `main`). The strain is the cluster repo; this is the branch containing `instances/<name>/` |
| **SERVICE**                         | Build                                    | Service to build: `openedx` or `mfe`                                                                                              |
| **LAUNCHPAD_CLI_VERSION**                 | Create, Build, Build All, Delete         | Git ref (branch/tag/SHA) of launchpad-cluster-template for the CLI (default: `main`)                                                    |
| **RUNNER_WORKFLOW_LABEL**           | All                                      | GitHub Actions runner label (default: `ubuntu-latest`). Use `self-hosted` for self-hosted runners                                 |
| **PICASSO_VERSION**                 | Build, Build All                         | Git ref of Picasso for image builds                                                                                               |
| **LAUNCHPAD_OPENCRAFT_MANIFESTS_VERSION** | Delete                                   | Git ref for OpenCraft manifests (default: `main`)                                                                                 |
| **EDX_PLATFORM_VERSION**            | Create                                   | edX Platform branch/tag (default: `release/teak.3`)                                                                               |
| **TUTOR_VERSION**                   | Create                                   | Tutor version (default from cluster template)                                                                                     |
| **INSTANCE_TEMPLATE_VERSION**       | Create                                   | Instance template version (default: `main`)                                                                                       |
| **CONFIG**                          | Update                                   | JSON object to merge into instance config (e.g. `{"KEY": "value"}`)                                                               |

### Strain and Repository

The **strain** is the cluster repository itself. The branch (`STRAIN_REPOSITORY_BRANCH`) determines which branch of the cluster repo is used when building images. For instance `my-instance`, the build uses `instances/my-instance/` from that branch.

## ArgoCD Project and Repository Connection

ArgoCD must be able to clone the cluster repository to sync applications. Configure it after installing ArgoCD and Argo Workflows.

### Step 1: Create or Use the Default Project

ArgoCD applications use a project (e.g. `launchpad-production`). The default project may already exist. To create one:

1. Log into the ArgoCD UI.
2. Go to **Settings** -> **Projects**.
3. Create a project or use the default.

### Step 2: Connect the Repository

1. In ArgoCD, go to **Settings** -> **Repositories**.
2. Click **Connect Repo**.
3. Choose the connection method:

#### GitHub (SSH Deploy Key)

1. **Connection method**: Via SSH
2. **Repository URL**: `git@github.com:your-org/launchpad-production-cluster.git`
3. **SSH private key**: Paste the private key (same content as `SSH_PRIVATE_KEY` if you use it for GitHub Actions)

To add the SSH key to GitHub as a Deploy Key:

- Go to your cluster repo -> **Settings** -> **Deploy keys**.
- Add the **public** key (`.pub` file).

For read-only access, you can create a deploy key with only clone permission. For write access (e.g. if ArgoCD writes back), enable write access.

#### GitHub (HTTPS with Personal Access Token)

1. **Connection method**: Via HTTPS
2. **Repository URL**: `https://github.com/your-org/launchpad-production-cluster.git`
3. **Username**: Your GitHub username (or `x-access-token` for fine-grained PATs)
4. **Password**: GitHub Personal Access Token with `repo` scope

### Step 3: Verify Connection

After adding the repository, ArgoCD should show it as connected. Applications that reference this repo will be able to sync.

### Step 4: Project Configuration

Ensure the project allows the repository:

1. Go to **Settings** -> **Projects** -> your project.
2. Under **Source Repositories**, add your cluster repository URL.
3. Under **Destinations**, add the cluster (e.g. `https://kubernetes.default.svc`).

## Related Documentation

- [Infrastructure Provisioning](provisioning.md) - Cluster creation and ArgoCD installation
- [Instance Provisioning](../instances/provisioning.md) - Creating instances
- [Instance Configuration](../instances/configuration.md) - config.yml, object storage, and manifests
- [Object Storage](../instances/configuration.md#object-storage) - Bucket provisioning vs Tutor S3 plugins
- [Instance Docker Images](../instances/docker-images.md) - Building images with Picasso

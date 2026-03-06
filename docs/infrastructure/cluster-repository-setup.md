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
2. Go to **Settings** → **Secrets and variables** → **Actions**.
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
| `LAUNCHPAD_MONGODB_HOST`                | Create Instance, Delete Instance                                    | MongoDB hostname (for direct connection)                              |
| `LAUNCHPAD_MONGODB_PORT`                | Create Instance, Delete Instance                                    | MongoDB port (default: `27017`)                                       |
| `LAUNCHPAD_MONGODB_PROVIDER`            | Create Instance, Delete Instance                                    | `digitalocean_api` or `atlas`                                         |
| `LAUNCHPAD_MONGODB_CLUSTER_ID`          | Create Instance, Delete Instance                                    | DigitalOcean MongoDB cluster ID (or Atlas project ID)                 |
| `LAUNCHPAD_MONGODB_REPLICA_SET`         | Create Instance, Delete Instance                                    | MongoDB replica set name                                              |
| `LAUNCHPAD_MONGODB_AUTH_SOURCE`         | Create Instance, Delete Instance                                    | MongoDB auth source (default: `admin`)                                 |
| `LAUNCHPAD_DIGITALOCEAN_TOKEN`          | Create Instance, Delete Instance                                    | DigitalOcean API token                                                |
| `LAUNCHPAD_STORAGE_TYPE`                | Create Instance, Delete Instance                                    | `s3` or `spaces`                                                      |
| `LAUNCHPAD_STORAGE_REGION`              | Create Instance, Delete Instance                                    | Region (e.g. `us-east-1`, `nyc3`)                                     |
| `LAUNCHPAD_STORAGE_ACCESS_KEY_ID`       | Create Instance, Delete Instance                                    | S3/Spaces access key ID                                               |
| `LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY`   | Create Instance, Delete Instance                                    | S3/Spaces secret access key                                           |
| `SSH_PRIVATE_KEY`                 | Create Instance, Build, Build All, Delete Instance, Update Instance | Private SSH key for cloning the cluster repo and private dependencies |

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
```

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

# Add deploy_key.pub as a Deploy Key in your repo (Settings → Deploy keys)
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
2. Go to **Settings** → **Projects**.
3. Create a project or use the default.

### Step 2: Connect the Repository

1. In ArgoCD, go to **Settings** → **Repositories**.
2. Click **Connect Repo**.
3. Choose the connection method:

#### GitHub (SSH Deploy Key)

1. **Connection method**: Via SSH
2. **Repository URL**: `git@github.com:your-org/launchpad-production-cluster.git`
3. **SSH private key**: Paste the private key (same content as `SSH_PRIVATE_KEY` if you use it for GitHub Actions)

To add the SSH key to GitHub as a Deploy Key:

- Go to your cluster repo → **Settings** → **Deploy keys**.
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

1. Go to **Settings** → **Projects** → your project.
2. Under **Source Repositories**, add your cluster repository URL.
3. Under **Destinations**, add the cluster (e.g. `https://kubernetes.default.svc`).

## Related Documentation

- [Infrastructure Provisioning](provisioning.md) - Cluster creation and ArgoCD installation
- [Instance Provisioning](../instances/provisioning.md) - Creating instances
- [Instance Configuration](../instances/configuration.md) - config.yml and manifests
- [Instance Docker Images](../instances/docker-images.md) - Building images with Picasso

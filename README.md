# Launchpad Cluster Template

A cookiecutter template for creating production-ready Open edX hosting clusters with automated instance management using GitOps principles.

## Project Intent

This project provides a complete solution for hosting multiple Open edX instances on Kubernetes clusters with:

- **Automated Infrastructure**: Terraform modules for AWS and DigitalOcean
- **GitOps Workflows**: ArgoCD and Argo Workflows for declarative deployments
- **Instance Management**: GitHub Actions for automated instance lifecycle
- **Multi-tenancy**: Secure RBAC and namespace isolation
- **Scalability**: Support for multiple instances per cluster

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Kubernetes     │    │   ArgoCD        │
│   Actions       │───▶│   Cluster        │───▶│   + Workflows   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Instance      │    │   Namespace      │    │   Open edX      │
│   Lifecycle     │    │   Management     │    │   Instances     │
│   Management    │    │   + RBAC         │    │   Deployment    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Repository Structure

```
launchpad-cluster-template/
├── cluster-template/           # Cookiecutter template for clusters
│   ├── launchpad-{{cookiecutter.cluster_slug_normalized}}-cluster/
│   │   ├── activate            # Cluster activation script
│   │   ├── infrastructure/     # Terraform infrastructure modules (after generation)
│   │   └── instances/          # Instance configurations
│   └── hooks/                  # Cookiecutter post-generation hooks
├── instance-template/          # Cookiecutter template for instances
│   └── {{cookiecutter.instance_slug}}/
│       ├── application.yml     # ArgoCD Application manifest
│       └── config.yml          # Instance configuration
├── manifests/                  # Kubernetes manifests
│   ├── argocd-*.yml            # ArgoCD configuration
│   ├── argo-*.yml              # Argo Workflows configuration
│   ├── openedx-*.yml           # Open edX RBAC
│   └── launchpad-*-template.yml      # Provision/deprovision workflows
├── tooling/                    # Python CLI package
│   ├── launchpad/                    # Source code
│   │   ├── cli/                # CLI commands
│   │   ├── config.py           # Configuration management
│   │   ├── kubernetes.py       # Kubernetes client
│   │   ├── password.py         # Password utilities
│   │   └── utils.py            # Utility functions
│   ├── tests/                  # Test suite
│   ├── pyproject.toml          # Project metadata and dependencies
│   └── uv.lock                 # Lock file
├── .github/workflows/          # GitHub Actions workflows
│   ├── create-instance.yml     # Instance creation workflow
└   └── delete-instance.yml     # Instance deletion workflow
```

## Quick Start

### 1. Install Launchpad CLI

The Launchpad CLI provides Python-based commands for managing clusters and instances.

**Install uv** (if not already installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Launchpad as a tool:

```bash
# Install from git repository
uv tool install git+https://github.com/open-craft/launchpad-cluster-template.git#subdirectory=tooling

# Set required environment variable
export LAUNCHPAD_CLUSTER_DOMAIN="your-cluster-domain.com"

# Verify installation
launchpad_install_argo --help
```

Install for contribution:

```bash
# Clone the repository
git clone https://github.com/open-craft/launchpad-cluster-template.git
cd launchpad-cluster-template/tooling

# Install with all dependencies
uv sync --all-groups

# Set required environment variable
export LAUNCHPAD_CLUSTER_DOMAIN="your-cluster-domain.com"

# Verify installation
launchpad_install_argo --help
```

### 2. Generate a Cluster

**Using Launchpad CLI**:
```bash
# Set required environment variable
export LAUNCHPAD_CLUSTER_DOMAIN="cluster.domain"

# Create cluster configuration
launchpad_create_cluster "Launchpad Production Cluster" "prod.cluster.domain"
```

**Using cookiecutter directly**:
```bash
# Install cookiecutter
pip install cookiecutter

# Generate cluster template
cookiecutter https://github.com/open-craft/launchpad-cluster-template.git --directory cluster-template
```

### 3. Set Up Infrastructure

```bash
# Navigate to your cluster's directory
cd your-cluster-name

# Navigate to the infrastructure directory
cd infrastructure

# Set up backend credentials via environment variables
# For AWS S3 backend:
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# For DigitalOcean Spaces backend:
export AWS_ACCESS_KEY_ID="your-spaces-access-key"
export AWS_SECRET_ACCESS_KEY="your-spaces-secret-key"

# Deploy infrastructure
tofu init
tofu plan
tofu apply
```

### 4. Install GitOps Tools

```bash
# Set required environment variable
export LAUNCHPAD_CLUSTER_DOMAIN="your-cluster-domain.com"

# Install both ArgoCD and Argo Workflows
launchpad_install_argo

# Or install selectively
launchpad_install_argo --argocd-only
launchpad_install_argo --workflows-only
```

### 5. Configure ArgoCD

The Launchpad commands will generate `application.yml` files for every instance with a project set to `launchpad-{{ environment }}`, so different instance environments within the same cluster can use different project or repository settings.

However, this means one have to configure each and every `launchpad-{{ environment }}` with repository settings per environment. For example, if the instance has the `project: launchpad-production` set, a `launchpad-production` project must exist in ArgoCD as well.

This is a manual work.

## Usage

### Instance Management

#### Creating Instances

**Using Launchpad CLI**:
```bash
# Create instance with default configuration
launchpad_create_instance my-instance \
  "https://github.com/your-org/your-cluster.git" \
  "My Open edX Platform"

# Create instance with custom Open edX version
launchpad_create_instance my-instance \
  "https://github.com/your-org/your-cluster.git" \
  "My Open edX Platform" \
  --edx-platform-repository "https://github.com/openedx/edx-platform.git" \
  --edx-platform-version "release/teak.3" \
  --tutor-version "v20.0.1"
```

**Using GitHub Actions**:
1. Go to your cluster repository's Actions tab
2. Select "Create Instance" workflow
3. Provide instance configuration
4. Monitor the workflow execution

#### Deleting Instances

**Using Launchpad CLI**:
```bash
# Delete instance
launchpad_delete_instance my-instance
```

**Using GitHub Actions**:
1. Go to your cluster repository's Actions tab
2. Select "Delete Instance" workflow
3. Provide instance name
4. Monitor the cleanup process

### Launchpad Commands

The project provides a comprehensive set of commands through the Python CLI:

**Cluster Management**:
```bash
# Create a new cluster configuration
launchpad_create_cluster <cluster_name> <cluster_domain> [options]
```

**GitOps Tools**:
```bash
# Install ArgoCD and Argo Workflows
launchpad_install_argo              # Install both
launchpad_install_argo --argocd-only         # Install ArgoCD only
launchpad_install_argo --workflows-only      # Install Argo Workflows only
```

**User Management**:
```bash
# Create ArgoCD user
launchpad_create_argo_user <username> [--role admin|developer|readonly] [--password PASSWORD]

# Update user permissions
launchpad_update_argo_user <username> --role admin|developer|readonly

# Delete Argo user
launchpad_delete_argo_user <username>
```

**Instance Management**:
```bash
# Create instance
launchpad_create_instance <name> <template_repository> <platform_name> [options]

# Delete instance
launchpad_delete_instance <name>
```

**Configuration**:

All commands can be configured via environment variables. See `tooling/launchpad/config.py` for available options:

```bash
# Required
export LAUNCHPAD_CLUSTER_DOMAIN="your-cluster-domain.com"

# Optional (with defaults shown)
export LAUNCHPAD_ARGOCD_VERSION="stable"
export LAUNCHPAD_ARGO_WORKFLOWS_VERSION="stable"
export LAUNCHPAD_OPENCRAFT_MANIFESTS_URL="https://raw.githubusercontent.com/open-craft/launchpad-cluster-template/main/manifests"

# Docker Registry (for private image pulls)
export LAUNCHPAD_DOCKER_REGISTRY="ghcr.io"  # Default: ghcr.io
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64_encoded_username:token"
```

**Docker Registry Credentials**:

The Launchpad CLI automatically configures cluster-wide Docker registry pull credentials to enable pulling private images from container registries. This is set up automatically during:

- **Cluster bootstrap**: When running `launchpad_install_argo`, credentials are configured for system namespaces (`argo`, `argocd`, `default`) and all existing non-system namespaces
- **Instance creation**: When running `launchpad_create_instance`, credentials are automatically configured for the new instance namespace

**Format**:

The `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS` must be a base64-encoded string in the format `username:token` or `username:password`. This is the same format used in Docker's `~/.docker/config.json` file.

**Examples**:

For GitHub Container Registry (GHCR):
```bash
# Generate credentials (replace USERNAME and TOKEN with your actual values)
echo -n "USERNAME:TOKEN" | base64
# Output: VVNFUk5BTUU6VE9LRU4=

export LAUNCHPAD_DOCKER_REGISTRY="ghcr.io"
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="VVNFUk5BTUU6VE9LRU4="
```

For Docker Hub:
```bash
# Generate credentials
echo -n "dockerhub_username:dockerhub_token" | base64

export LAUNCHPAD_DOCKER_REGISTRY="docker.io"
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64_encoded_credentials"
```

For other registries (e.g., AWS ECR, Google GCR, Azure ACR):
```bash
# Use the registry-specific authentication format
# For AWS ECR, you might use an IAM role token
# For GCR, use a service account JSON key
# Format: echo -n "username:token" | base64

export LAUNCHPAD_DOCKER_REGISTRY="your-registry.cluster.domain"
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64_encoded_credentials"
```

**How it works**:

1. The CLI creates a Kubernetes `Secret` of type `kubernetes.io/dockerconfigjson` in each namespace
2. The secret is automatically attached to ServiceAccounts (`default` and `workflow-executor`) via `imagePullSecrets`
3. All pods using these ServiceAccounts can now pull images from the private registry
4. The configuration is idempotent - running the setup multiple times is safe

**Note**: If `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS` is not set, the registry credential setup is skipped. This is safe for clusters that only use public images.

### Automatic Kubeconfig Management

The Launchpad CLI includes kubeconfig detection and setup:

**Detection Order**:
1. **Terraform/OpenTofu Output**: Checks for `tofu` or `terraform` commands and retrieves the `kubeconfig` output
2. **Environment Variable**: Uses `KUBECONFIG_CONTENT` (supports both base64-encoded and plain text)
3. **Existing Configuration**: Falls back to `~/.kube/config` if present

**Local Development**:
```bash
# Use Terraform/OpenTofu
cd your-cluster/infrastructure
tofu apply  # or terraform apply
cd ../..
launchpad_create_instance [...]  # Automatically uses Terraform output
```

**CI/CD Environments**:

The CLI automatically handles base64-encoded kubeconfig in CI/CD:

```yaml
env:
  KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_CONTENT }}
run: launchpad_create_instance ...
```

**Error Handling**:

If no kubeconfig can be found, the CLI provides a helpful error message:

```
No kubeconfig available. Please ensure one of the following:
1. Run this command from a directory with infrastructure directory present
2. Set KUBECONFIG_CONTENT environment variable
3. Have a valid kubeconfig at ~/.kube/config
```

## Security & RBAC

- **Namespace Isolation**: Each instance runs in its own namespace
- **RBAC**: Proper role-based access control for all resources
- **Secret Management**: Secure handling of database credentials
- **Network Policies**: Isolated network access between instances

### User Roles

The system supports three user roles with different permission levels for ArgoCD:

#### Admin Role
- **ArgoCD**: Full access to all applications and projects
- **Permissions**: Create, read, update, delete all applications and projects

#### Developer Role
- **ArgoCD**: Access to assigned applications and projects
- **Permissions**: Create, read, update, delete assigned applications and projects

#### Readonly Role
- **ArgoCD**: Read-only access to applications and projects
- **Permissions**: View applications and projects only

### Updating User Permissions

If you need to update a user's permissions after creation:

```bash
# Update user to admin role
launchpad_update_argo_user_permissions username admin

# Update user to developer role
launchpad_update_argo_user_permissions username developer

# Update user to readonly role
launchpad_update_argo_user_permissions username readonly
```

### Workflow Manifest Files

Instance workflows are defined in separate YAML manifest files in the `manifests/` directory:

**Provision Workflows:**
- `launchpad-mysql-provision-workflow.yml`: MySQL database provision workflow
- `launchpad-mongodb-provision-workflow.yml`: MongoDB database provision workflow
- `launchpad-storage-provision-workflow.yml`: Storage bucket provision workflow

**Deprovision Workflows:**
- `launchpad-mysql-deprovision-workflow.yml`: MySQL database deprovision workflow
- `launchpad-mongodb-deprovision-workflow.yml`: MongoDB database deprovision workflow
- `launchpad-storage-deprovision-workflow.yml`: Storage bucket deprovision workflow

These manifests use template variables with the `LAUNCHPAD_INSTANCE_` prefix (e.g., `{{LAUNCHPAD_INSTANCE_NAME}}`, `{{LAUNCHPAD_INSTANCE_MYSQL_DATABASE}}`) and are applied using the `__launchpad_kubectl_apply_from_url` function, following the established pattern for remote manifest management.

## Cloud Support

### DigitalOcean
- **Kubernetes**: DigitalOcean Kubernetes (DOKS)
- **Databases**: Managed MySQL and MongoDB
- **Storage**: DigitalOcean Spaces
- **Networking**: VPC with private/public subnets

### AWS
- **Kubernetes**: Amazon EKS
- **Databases**: RDS MySQL and DocumentDB
- **Storage**: S3 buckets
- **Networking**: VPC with private/public subnets

## Database Provider Support

### MongoDB Providers

The system supports multiple MongoDB providers with automatic detection:

- **`digitalocean_api`**: DigitalOcean API-based database management
- **`atlas`**: MongoDB Atlas API-based database management

**Provider is automatically detected** based on your configuration.

#### Quick Configuration

**DigitalOcean-managed MongoDB**:
```bash
export LAUNCHPAD_MONGODB_HOST="mongodb.cluster.domain"
export LAUNCHPAD_MONGODB_PORT="27017"
export LAUNCHPAD_MONGODB_ADMIN_USER="admin"
export LAUNCHPAD_MONGODB_ADMIN_PASSWORD="secure_password"
export LAUNCHPAD_MONGODB_CLUSTER_ID="abc12345-xyz67890"
export LAUNCHPAD_DIGITALOCEAN_TOKEN="dop_v1_your_token"
```

**MongoDB Atlas via CLI**:
```bash
export LAUNCHPAD_ATLAS_PUBLIC_KEY="your_public_key"
export LAUNCHPAD_ATLAS_PRIVATE_KEY="your_private_key"
export LAUNCHPAD_ATLAS_PROJECT_ID="your_project_id"
export LAUNCHPAD_ATLAS_CLUSTER_NAME="Cluster0"
```

> **Note**: Atlas provisioning uses the [MongoDB Atlas CLI](https://www.mongodb.com/docs/atlas/cli/current/) for user management. The CLI is installed automatically from the [official MongoDB package repository](https://www.mongodb.com/docs/atlas/cli/current/install-atlas-cli/). Databases are created automatically on first write by your application.

### Storage Providers

The system automatically computes storage endpoint URLs based on provider type:

- **DigitalOcean Spaces**: Automatic endpoint formatting (`https://{region}.digitaloceanspaces.com`)
- **AWS S3**: Uses AWS default endpoints

**Configuration**:
```bash
export LAUNCHPAD_STORAGE_TYPE="spaces"  # or "s3"
export LAUNCHPAD_STORAGE_REGION="nyc3"  # or "us-east-1"
export LAUNCHPAD_STORAGE_ACCESS_KEY_ID="your_key"
export LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY="your_secret"
```

## GitHub Actions Workflows

The repository includes automated GitHub Actions workflows for instance lifecycle management using the Python CLI.

### Create Instance Workflow

**Triggers**: Manual workflow dispatch

**Inputs**:
- `instance_name`: Unique DNS-compliant instance identifier
- `template_repository`: Repository containing the instance template
- `platform_name`: Display name for the Open edX platform
- `edx_platform_repository`: Custom edX Platform fork (optional)
- `edx_platform_version`: Branch/tag to deploy (optional)
- `tutor_version`: Tutor version to use (optional)

**What it does**:
1. Installs Launchpad CLI using `uv tool install`
2. Configures kubectl with cluster credentials
3. Creates namespace with RBAC policies
4. Generates instance configuration using cookiecutter
5. Applies provision workflows (MySQL, MongoDB, Storage)
6. Creates ArgoCD Application for GitOps deployment
7. Waits for provision workflows to complete

**Usage**:
1. Go to Actions → Create Instance
2. Click "Run workflow"
3. Fill in the required parameters
4. Monitor the workflow execution and logs

### Delete Instance Workflow

**Triggers**: Manual workflow dispatch

**Inputs**:
- `instance_name`: Name of the instance to delete
- `confirm_deletion`: Must match instance name to proceed (safety check)

**What it does**:
1. Validates deletion confirmation
2. Installs Launchpad CLI using `uv tool install`
3. Configures kubectl with cluster credentials
4. Deletes ArgoCD Application
5. Triggers deprovision workflows (MySQL, MongoDB, Storage)
6. Waits for deprovision workflows to complete
7. Cleans up Kubernetes resources (namespace, RBAC, secrets)
8. Removes all instance artifacts

**Usage**:
1. Go to Actions → Delete Instance
2. Click "Run workflow"
3. Enter instance name and confirm by typing it again
4. Monitor the workflow execution and logs

## Configuration

### Terraform Backend Configuration

The infrastructure uses Terraform/OpenTofu with S3-compatible backends for state storage. To avoid storing sensitive credentials in the state files, **backend credentials must be provided via environment variables**.

#### AWS S3 Backend

For AWS S3 backends, set these environment variables:

```bash
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
```

#### DigitalOcean Spaces Backend

For DigitalOcean Spaces backends, set these environment variables:

```bash
export AWS_ACCESS_KEY_ID="your-spaces-access-key"
export AWS_SECRET_ACCESS_KEY="your-spaces-secret-key"
```

#### Alternative: Backend Config File

You can also create a separate backend configuration file (e.g., `backend.hcl`) that's not committed to version control:

```hcl
# backend.hcl (add to .gitignore)
bucket     = "tfstate-launchpad-your-cluster-cluster-production"
key        = "terraform.tfstate"
access_key = "your-access-key"
secret_key = "your-secret-key"
region     = "your-region"
```

Then initialize with:
```bash
tofu init -backend-config=backend.hcl
```

### Required GitHub Secrets

For GitHub Actions workflows to function properly, configure the following secrets in your repository settings:

**Kubernetes Access**:

The Launchpad CLI automatically detects and configures kubeconfig from multiple sources:

1. **Terraform/OpenTofu Output** (Recommended): If you're in a directory with Terraform/OpenTofu that has a `kubeconfig` output, it will be used automatically
2. **Environment Variable**: Set `KUBECONFIG_CONTENT` (base64-encoded or plain text)
3. **Existing Config**: Falls back to `~/.kube/config` if present

For GitHub Actions, configure:
- `KUBECONFIG_CONTENT`: Base64-encoded kubeconfig file for cluster access
  ```bash
  # Generate the secret value:
  cat ~/.kube/config | base64 -w 0  # Linux
  cat ~/.kube/config | base64       # macOS
  ```
- `LAUNCHPAD_CLUSTER_DOMAIN`: Your cluster's domain name (e.g., `prod.cluster.domain`)

**Note**: The Launchpad CLI will automatically handle kubeconfig setup, so no need to manually configure kubectl in most cases.

**MySQL Database** (if using MySQL):
- `LAUNCHPAD_MYSQL_HOST`: MySQL server hostname
- `LAUNCHPAD_MYSQL_PORT`: MySQL server port (default: `3306`)
- `LAUNCHPAD_MYSQL_ADMIN_USER`: MySQL admin username
- `LAUNCHPAD_MYSQL_ADMIN_PASSWORD`: MySQL admin password

**MongoDB Database** (if using MongoDB):
- `LAUNCHPAD_MONGODB_HOST`: MongoDB server hostname
- `LAUNCHPAD_MONGODB_PORT`: MongoDB server port (default: `27017`)
- `LAUNCHPAD_MONGODB_ADMIN_USER`: MongoDB admin username
- `LAUNCHPAD_MONGODB_ADMIN_PASSWORD`: MongoDB admin password
- `LAUNCHPAD_MONGODB_REPLICA_SET`: MongoDB replica set name
- `MONGODB_AUTH_SOURCE`: MongoDB auth source (default: `admin`)
- `LAUNCHPAD_MONGODB_CLUSTER_ID`: (Optional) DigitalOcean MongoDB cluster ID for API-based management
- `LAUNCHPAD_DIGITALOCEAN_TOKEN`: (Optional) DigitalOcean API token if using DO managed databases

**Storage** (S3/Spaces):
- `LAUNCHPAD_STORAGE_TYPE`: Storage type (`s3` or `spaces`)
- `LAUNCHPAD_STORAGE_REGION`: Storage region (e.g., `us-east-1` or `nyc3`)
- `LAUNCHPAD_STORAGE_ACCESS_KEY_ID`: Storage access key ID
- `LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY`: Storage secret access key

**Docker Registry** (Required for private image pulls):
- `LAUNCHPAD_DOCKER_REGISTRY`: Docker registry hostname (default: `ghcr.io`)
  - Examples: `ghcr.io`, `docker.io`, `registry.cluster.domain`
- `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS`: Base64-encoded credentials in format `username:token`
  - Generate with: `echo -n "username:token" | base64`
  - For GitHub Container Registry: Use a GitHub Personal Access Token (PAT) with `read:packages` permission
  - For Docker Hub: Use Docker Hub username and access token
  - For other registries: Follow registry-specific authentication requirements

**Example for GitHub Container Registry**:
```bash
# Create a GitHub PAT with 'read:packages' permission
# Then generate the credentials:
echo -n "github_username:ghp_your_personal_access_token" | base64

# Set in GitHub Secrets:
LAUNCHPAD_DOCKER_REGISTRY="ghcr.io"
LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="<base64_output_from_above>"
```

> **Note**: Registry credentials are automatically configured cluster-wide during `launchpad_install_argo` and for each new instance namespace during `launchpad_create_instance`. The credentials are stored as Kubernetes secrets and attached to ServiceAccounts to enable automatic image pulls.

**Terraform Backend** (Required for state storage):
- `AWS_ACCESS_KEY_ID`: Backend storage access key (same as `LAUNCHPAD_STORAGE_ACCESS_KEY_ID`)
- `AWS_SECRET_ACCESS_KEY`: Backend storage secret key (same as `LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY`)

> **Note**: The backend credentials use the same values as your storage credentials since both use S3-compatible APIs.

## Troubleshooting

### Common Issues

1. **Terraform apply fails**: Check cloud provider credentials
2. **kubectl not working**: Verify kubeconfig is set correctly
3. **GitHub Actions fail**: Check that KUBECONFIG_CONTENT secret is set
4. **ArgoCD not accessible**: Check ingress configuration and DNS

### Getting Help

- Check GitHub Actions logs
- Verify terraform outputs
- Check ArgoCD and Argo Workflows status
- Review RBAC permissions

## Development

### Install pre-commit

This repo uses [pre-commit](https://pre-commit.com/) to ensure the code is formatted and up to standards before it is being committed.

Once pre-commit is installed, execute `pre-commit install` to setup the git commit hooks. Then, execute `pre-commit install -t commit-msg` to allow the `commit-msg` state.

### Setting Up Development Environment

The Launchpad CLI is written in Python and uses `uv` for dependency management:

```bash
# Clone the repository
git clone https://github.com/open-craft/launchpad-cluster-template.git
cd launchpad-cluster-template/tooling

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all dependencies (including dev group)
uv sync --all-groups

# Run tests
uv run pytest

# Run linter
uv run pylint launchpad/cli/*.py

# Format code
uv run black launchpad/
uv run isort launchpad/
```

### Running Tests

```bash
# Run all tests
cd tooling
uv run pytest

# Run specific test file
uv run pytest tests/test_password.py

# Run with coverage
uv run pytest --cov=launchpad --cov-report=term --cov-report=xml
```

### Continuous Integration

The project uses GitHub Actions for automated testing:

**Test Workflow** (`.github/workflows/test-tooling.yml`):
- Triggers on push/PR to `main` or `develop` branches
- Runs on Python 3.12
- Executes full test suite with coverage reporting
- Runs pylint for code quality checks
- Uploads coverage reports to Codecov

The workflow automatically runs when changes are made to the `tooling/` directory.

### Code Quality

The project maintains high code quality standards:

- **Linting**: Pylint with custom rules (`.pylintrc`)
- **Formatting**: Black and isort
- **Type Hints**: Full type annotations
- **Score**: 10.00/10 pylint score

```bash
# Check code quality
uv run pylint launchpad/
uv run black --check launchpad/
uv run isort --check launchpad/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b your-name/new-feature`)
3. Make your changes
4. Run tests and linters: `uv run pytest && uv run pylint launchpad/`
5. Format code: `uv run black launchpad/ && uv run isort launchpad/`
6. Commit your changes (`git commit -m 'Add new feature'`)
7. Push to the branch (`git push origin your-name/new-feature`)
8. Open a Pull Request

## License

This project is licensed under the AGPL-v3.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Open edX](https://openedx.org/) - The learning platform
- [Tutor](https://docs.tutor.overhang.io/) - The deployment tool
- [Picasso](https://github.com/eduNEXT/picasso) - GitHub Actions for Image building
- [DryDock](https://github.com/eduNEXT/drydock) - Tutor plugins for better OpenedX installations in Kubernetes
- [ArgoCD](https://argo-cd.readthedocs.io/) - GitOps continuous delivery
- [Argo Workflows](https://argoproj.github.io/argo-workflows/) - Workflow engine to provision resources

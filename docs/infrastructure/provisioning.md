# Infrastructure Provisioning

Infrastructure provisioning sets up a complete Kubernetes cluster environment for hosting Open edX instances. This includes creating the cluster configuration, deploying the underlying infrastructure (Kubernetes cluster, databases, storage), and installing ArgoCD and Argo Workflows.

The provisioning process consists of three main phases:

1. **Cluster Configuration**: Generate cluster configuration files using cookiecutter templates
2. **Infrastructure Deployment**: Deploy Kubernetes cluster and supporting infrastructure using Terraform/OpenTofu
3. **GitOps Tools Installation**: Install and configure ArgoCD and Argo Workflows for automated deployments

## Prerequisites

Before provisioning infrastructure, ensure you have:

- **Launchpad CLI**: Installed and configured (see [Quick Start](../index.md#quick-start))
- **Cookiecutter**: Installed for cluster template generation (`pip install cookiecutter`)
- **Cloud Provider Access**: Valid credentials for AWS or DigitalOcean
- **Terraform/OpenTofu**: Installed (OpenTofu is recommended)
- **kubectl**: Installed
- **Git Repository**: Access to a GitHub organization with repository create access (will create the repository during provisioning)

## Provisioning Steps

### Step 1: Create Cluster Configuration

The first step is to generate the cluster configuration using the `launchpad_create_cluster` command. This creates a directory structure with Terraform modules, GitHub Actions workflows, and configuration files.

**Install the CLI** (if not already installed):

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Launchpad CLI as a tool (persistent)
uv tool install git+https://github.com/open-craft/launchpad-cluster-template.git#subdirectory=tooling

# Or run without installing (one-off)
uvx --from git+https://github.com/open-craft/launchpad-cluster-template.git#subdirectory=tooling launchpad_create_cluster --help
```

**Create cluster configuration**:

```bash
# Create cluster with custom options
launchpad_create_cluster "Launchpad Production Cluster" "cluster.domain" \
  --environment production \
  --cloud-provider aws \
  --cloud-region us-east-1 \
  --github-organization your-org \
  --output-dir ./clusters
```

**Command Options**:

- `cluster_name`: Display name for the cluster
- `cluster_domain`: Domain name for the cluster (e.g., `cluster.domain`)
- `--environment`: Environment name (default: `production`)
- `--cloud-provider`: Cloud provider - `aws` or `digitalocean`
- `--cloud-region`: Region for the cloud provider
- `--harmony-module-version`: Harmony Terraform module version/commit hash
- `--opencraft-module-version`: OpenCraft Terraform module version
- `--picasso-version`: Picasso version for image building
- `--tutor-version`: Tutor version to use
- `--github-organization`: GitHub organization name
- `--github-repository`: Custom GitHub repository URL (auto-generated if not provided)
- `--output-dir`: Directory where cluster configuration will be created

**What This Creates**:

- Cluster directory with normalized name (e.g., `launchpad-production-cluster`)
- Terraform infrastructure modules for AWS or DigitalOcean
- GitHub Actions workflows for building images and managing instances
- Instance template directory structure
- Configuration files and documentation

After pushing the repository to GitHub, configure [GitHub Actions secrets and ArgoCD](cluster-repository-setup.md) before creating instances.

### Step 2: Deploy Infrastructure

After generating the cluster configuration, deploy the infrastructure using Terraform or OpenTofu.

**Navigate to Infrastructure Directory**:

```bash
cd launchpad-production-cluster/infrastructure
```

**Configure Backend Credentials**:

Backend credentials must be provided via environment variables or `backend.hcl` (recommended) to avoid storing them in state files:

```hcl
bucket     = "tfstate-bucket-name"
key        = "terraform.tfstate"
access_key = "access-key"
secret_key = "secret-key"
```

**Initialize and Deploy**:

```bash
# Initialize Terraform/OpenTofu
tofu init -backend-config=backend.hcl

# Review the deployment plan
tofu plan

# Apply the infrastructure
tofu apply
```

**What Gets Deployed**:

- **Kubernetes Cluster**: EKS (AWS) or DOKS (DigitalOcean)
- **Databases**: Managed MySQL and MongoDB instances
- **Storage**: S3 buckets or DigitalOcean Spaces
- **Networking**: VPC with private/public subnets, load balancers
- **Harmony Components**: Ingress controllers, monitoring (optional), backups (optional)

**Important**: After deployment completes, note the `.kubeconfig`will be created. You'll need this to access the cluster.

### Step 3: Configure kubectl

Configure `kubectl` to access your newly created cluster:

```bash
# Activate the configuration
source ../activate

# Verify cluster access
kubectl get nodes
```

### Step 4: Install ArgoCD and Argo Workflows

Install the GitOps tools required for managing Open edX instances.

**Set Required Environment Variable**:

```bash
export LAUNCHPAD_CLUSTER_DOMAIN="cluster.domain"
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64 encoded docker registry credentials"
```

**Install Both Tools**:

```bash
# Install both ArgoCD and Argo Workflows
launchpad_install_argo
```

**Or, Install Selectively**:

```bash
# Install only ArgoCD
launchpad_install_argo --argocd-only

# Install only Argo Workflows
launchpad_install_argo --workflows-only
```

**What Gets Installed**:

**ArgoCD**:
- ArgoCD namespace and core components
- Ingress configuration for web UI access
- Admin password (auto-generated if not provided via `LAUNCHPAD_ARGO_ADMIN_PASSWORD`)
- Base configuration
- Docker registry pull credentials

**Argo Workflows**:
- Argo Workflows namespace and core components
- Ingress configuration for workflow UI
- Admin authentication setup
- Workflow executor service account and token
- Provisioning/deprovisioning workflow templates (MySQL, MongoDB, Storage)
- Docker registry pull credentials

**Access the UIs**:

After installation, you can access:

- **ArgoCD**: `https://argocd.cluster.domain`
- **Argo Workflows**: `http://localhost:2746` (after `kubectl port-forward svc/argo-server 2746:2746 -n argo`)

Use the admin password (displayed during installation or set via `LAUNCHPAD_ARGO_ADMIN_PASSWORD`) to log in.

### Step 5: Configure ArgoCD Projects and Repository

ArgoCD must be able to clone the cluster repository to sync applications. Configure the repository connection and project before creating instances.

See [Cluster Repository Setup](cluster-repository-setup.md#argocd-project-and-repository-connection) for detailed instructions on:

- Connecting the repository via SSH (GitHub deploy key)
- Configuring the ArgoCD project
- Verifying the connection

### Step 6: Verify Installation

Verify that all components are installed and functioning:

```bash
# Check ArgoCD pods
kubectl get pods -n argocd

# Check Argo Workflows pods
kubectl get pods -n argo

# Check workflow templates
kubectl get clusterworkflowtemplates

# Verify ingress
kubectl get ingress -n argocd
kubectl get ingress -n argo
```

## Creating ArgoCD Users

After installing ArgoCD and Argo Workflows, you can create ArgoCD users using the `launchpad_create_argo_user` command.

### Basic Usage

**Create a user with default role (developer)**:

```bash
# Set required environment variable
export LAUNCHPAD_CLUSTER_DOMAIN="cluster.domain"

# Create user (will prompt for password)
launchpad_create_argo_user john.doe
```

**Create a user with specific role and password**:

```bash
# Create admin user
launchpad_create_argo_user admin.user \
  --role admin \
  --password "secure-password"

# Create developer user
launchpad_create_argo_user developer.user \
  --role developer \
  --password "secure-password"

# Create readonly user
launchpad_create_argo_user viewer.user \
  --role readonly \
  --password "secure-password"
```

### User Roles

The system supports three user roles with different ArgoCD permission levels:

**Admin Role**:
- Full access to all applications and projects
- Create, read, update, delete all applications and projects

**Developer Role**:
- Access to assigned applications and projects
- Create, read, update, delete assigned applications and projects

**Readonly Role**:
- Read-only access to applications and projects
- View applications and projects only

### What Gets Created

When you create a user, the following resources are created:

1. **ArgoCD Account**: User account configured in ArgoCD with login capability
2. **ArgoCD RBAC**: Role-based access control policies for ArgoCD

### After User Creation

After creating a user, restart the ArgoCD server pod to apply the login changes:

```bash
kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server
```

### Managing Users

**Update user permissions**:

```bash
# Update user role
launchpad_update_argo_user john.doe --role admin

# Update user password
launchpad_update_argo_user john.doe --password "new-password"
```

**Delete a user**:

```bash
# Delete user (will prompt for confirmation)
launchpad_delete_argo_user john.doe

# Force delete without confirmation
launchpad_delete_argo_user john.doe --force
```

### User Access

Users can access ArgoCD via:

- **ArgoCD Web UI**: `https://argocd.cluster.domain` (or your cluster domain)

## Configuration

### Environment Variables

**Required**:
- `LAUNCHPAD_CLUSTER_DOMAIN`: Cluster domain name (e.g., `cluster.domain`)

**Optional**:

- `LAUNCHPAD_ARGO_ADMIN_PASSWORD`: Admin password for ArgoCD and Argo Workflows (auto-generated if not set)
- `LAUNCHPAD_ARGOCD_VERSION`: ArgoCD version (default: `stable`)
- `LAUNCHPAD_ARGO_WORKFLOWS_VERSION`: Argo Workflows version (default: `stable`)
- `LAUNCHPAD_OPENCRAFT_MANIFESTS_URL`: Base URL for OpenCraft manifests (default: GitHub raw content URL)
- `LAUNCHPAD_DOCKER_REGISTRY`: Docker registry hostname (default: `ghcr.io`)
- `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS`: Base64-encoded registry credentials for private image pulls

### Terraform Variables

The infrastructure modules require various variables. See the `variables.tf` file in your infrastructure directory for a complete list. Common variables include:

- Cloud provider credentials
- Cluster name and domain
- Resource sizing (node pools, database instances)
- Monitoring and backup configuration
- Network configuration

## Troubleshooting

### Cluster Configuration Issues

**Template Generation Fails**:

- Ensure cookiecutter is installed (see [Prerequisites](#prerequisites))
- Check that the template repository is accessible
- Review error messages for missing required variables

**Missing Configuration Files**:

- Ensure you're in the correct directory after cluster creation
- Verify all required files were generated in the cluster directory

### Infrastructure Deployment Issues

**Terraform/OpenTofu Errors**:

- **Backend Connection**: Verify backend credentials are set correctly
- **Provider Credentials**: Ensure cloud provider credentials are valid
- **Resource Limits**: Check if you've hit cloud provider quotas
- **Network Issues**: Verify network connectivity to cloud provider APIs

**Common Solutions**:

```bash
# Re-initialize if backend configuration changed
tofu init -backend-config=backend.hcl -reconfigure

# Check Terraform state
tofu state list

# Validate configuration
tofu validate
```

**Kubernetes Cluster Not Accessible**:

- Verify the cluster was created successfully in your cloud provider console
- Check that kubeconfig was generated correctly
- Ensure network connectivity to the cluster API server
- Check that DNS records are pointing to the Kubernetes cluster

### ArgoCD/Argo Workflows Installation Issues

**Installation Fails**:

- **kubectl Access**: Verify `kubectl` can access the cluster
- **Namespace Conflicts**: Check if namespaces already exist
- **Manifest URLs**: Verify manifest URLs are accessible
- **Resource Quotas**: Ensure cluster has sufficient resources

**Check Installation Status**:

```bash
# Check ArgoCD installation
kubectl get pods -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server

# Check Argo Workflows installation
kubectl get pods -n argo
kubectl logs -n argo -l app=argo-server
```

**UI Not Accessible**:

- **Ingress Issues**: Check ingress controller is running
- **DNS Configuration**: Verify DNS records point to the ingress
- **TLS Certificates**: Check Let's Encrypt certificate status
- **Firewall Rules**: Ensure ports 80/443 are accessible

**Workflow Templates Not Found**:

```bash
# Verify templates were installed
kubectl get clusterworkflowtemplates

# Re-install templates
launchpad_install_argo --workflows-only
```

**Password Issues**:

- If password was auto-generated, check the CLI output for the generated password
- To set a custom password: `export LAUNCHPAD_ARGO_ADMIN_PASSWORD="your-password"`
- To reset password, re-run `launchpad_install_argo` with a new password

### Registry Credentials Issues

**Private Image Pull Failures**:

- Verify `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS` is set correctly (base64-encoded)
- Check that credentials are valid and have appropriate permissions
- Verify secrets were created in namespaces:

```bash
kubectl get secrets -n argocd
kubectl get secrets -n argo
```

## Next Steps

After successfully provisioning infrastructure:

1. **Configure ArgoCD Projects**: Set up projects for each environment
2. **Create First Instance**: Use `launchpad_create_instance` to create your first Open edX instance
3. **Set Up Monitoring**: Configure monitoring and alerting if not done during infrastructure deployment
4. **Backup Configuration**: Set up backup schedules if Velero was installed

See the [Instance Provisioning](../instances/provisioning.md) documentation for creating Open edX instances.

## Related Documentation

- [Infrastructure Overview](index.md) -  Core components (Kubernetes, ArgoCD, Argo Workflows)
- [Deprovisioning](deprovisioning.md) -  Removing cluster infrastructure
- [Cluster Overview](../cluster/index.md) -  Post-provisioning cluster operations
- [Instance Provisioning](../instances/provisioning.md) -  Creating Open edX instances

## See Also

- [Cluster Authentication](../cluster/authentication.md) -  kubeconfig and Argo users
- [Cluster Configuration](../cluster/configuration.md) -  Environment variables and Terraform
- [Custom Resources](custom-resources.md) -  Workflow templates and manifests

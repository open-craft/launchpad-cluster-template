# Instance Provisioning

Provisioning creates and configures the necessary resources for a new Open edX instance. This includes setting up databases and users for MySQL and MongoDB, storage buckets, Kubernetes namespaces, and RBAC policies. The provisioning process is automated through Argo Workflows and executed when creating a new instance.

The provisioning system handles:

- **MySQL Database**: Creates database and user with appropriate permissions
- **MongoDB Database**: Creates databases and user with appropriate permissions
- **Storage Buckets**: Creates S3-compatible storage buckets (AWS S3 or DigitalOcean Spaces)
- **Kubernetes Resources**: Sets up namespaces, RBAC policies, and service accounts

All provisioning workflows run in parallel and must complete successfully before the instance can be built and deployed.

!!! note "Object storage uses tutor-contrib-s3 keys"
    Instance `config.yml` stores Tutor `S3_*` / `OPENEDX_AWS_*` settings (seeded from `LAUNCHPAD_STORAGE_*` at create time). The same keys drive Open edX uploads and Launchpad bucket workflows. See [Object Storage](configuration.md#object-storage).

## Provisioning Steps

### Prerequisites

Before provisioning an instance, ensure the following are configured:

1. **Kubernetes Cluster**: A running Kubernetes cluster with ArgoCD and Argo Workflows installed
2. **Database Access**: Admin credentials for MySQL and MongoDB servers
3. **Storage Credentials**: Access keys for S3-compatible storage (AWS S3 or DigitalOcean Spaces)
4. **Environment Variables**: Required configuration variables set (see below)

### Required Environment Variables

**Docker Registry**:
```bash
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64-encoded user:password"
```

**MySQL Database**:
```bash
export LAUNCHPAD_MYSQL_HOST="mysql.cluster.domain"
export LAUNCHPAD_MYSQL_PORT="3306"
export LAUNCHPAD_MYSQL_ROOT_USER="root"
export LAUNCHPAD_MYSQL_ROOT_PASSWORD="secure_password"
```

**MongoDB Database** (DigitalOcean):
```bash
export LAUNCHPAD_MONGODB_HOST="mongodb.cluster.domain"
export LAUNCHPAD_MONGODB_PORT="27017"
export LAUNCHPAD_MONGODB_ADMIN_USER="admin"
export LAUNCHPAD_MONGODB_ADMIN_PASSWORD="secure_password"
export LAUNCHPAD_MONGODB_CLUSTER_ID="abc12345-xyz67890"
export LAUNCHPAD_MONGODB_AUTH_SOURCE="admin"
export LAUNCHPAD_DIGITALOCEAN_TOKEN="dop_v1_your_token"
```

**MongoDB Database** (MongoDB Atlas):
```bash
export LAUNCHPAD_ATLAS_PUBLIC_KEY="your_public_key"
export LAUNCHPAD_ATLAS_PRIVATE_KEY="your_private_key"
export LAUNCHPAD_ATLAS_PROJECT_ID="your_project_id"
export LAUNCHPAD_ATLAS_CLUSTER_NAME="Cluster0"
```

**Storage** (seeds tutor-contrib-s3 settings in `config.yml` at create time):
```bash
export LAUNCHPAD_STORAGE_TYPE="spaces"  # or "s3"
export LAUNCHPAD_STORAGE_REGION="nyc3"  # or "us-east-1"
export LAUNCHPAD_STORAGE_ACCESS_KEY_ID="your_key"
export LAUNCHPAD_STORAGE_SECRET_ACCESS_KEY="your_secret"
```

Use `spaces` for DigitalOcean Spaces (`S3_HOST={region}.digitaloceanspaces.com`) and `s3` for AWS (`S3_HOST` empty). After creation, edit the Tutor keys in `config.yml` if needed; Launchpad derives the workflow provider from whether `S3_HOST` contains `digitaloceanspaces.com`. See [Object Storage](configuration.md#object-storage).

### Provisioning Process

The provisioning process is automatically executed when creating a new instance using the `launchpad_create_instance` command or the GitHub Actions workflow (recommended). The process follows these steps:

#### 1. Namespace and RBAC Setup

- Creates a Kubernetes namespace for the instance
- Configures RBAC policies to allow Argo Workflows to manage resources
- Sets up service accounts and permissions

#### 2. Workflow Creation

Three provision workflows are created in parallel:

- **MySQL Provision Workflow**: Creates the MySQL database and user
- **MongoDB Provision Workflow**: Creates MongoDB databases and user
- **Storage Provision Workflow**: Creates the storage bucket

Each workflow is parameterized with instance-specific configuration values extracted from the instance configuration file.

#### 3. Workflow Execution

The workflows execute the following operations:

**MySQL Provisioning**:
- Connects to the MySQL server using admin credentials
- Creates the database specified in the instance configuration
- Creates a user with appropriate permissions

**MongoDB Provisioning**:
- Detects the MongoDB provider (DigitalOcean API, Atlas, or direct connection)
- Creates the main database and forum database
- Creates a user with appropriate permissions
- For API-based providers, uses the provider's API to manage users

**Storage Provisioning**:
- Creates an S3-compatible storage bucket named from `S3_STORAGE_BUCKET` in the instance config
- Derives provider from `S3_HOST` (`spaces` if the host contains `digitaloceanspaces.com`, otherwise AWS `s3`)
- Uses a custom endpoint built from `S3_HOST` / `S3_PORT` / `S3_USE_SSL` when a host is set; AWS with an empty host uses default endpoints
- Enables versioning for AWS S3 when possible; skips versioning for Spaces
- Leaves the bucket private by default

#### 4. Workflow Completion

The system waits for all workflows to complete successfully. If any workflow fails, the provisioning process is aborted and an error is reported.

#### 5. Configuration Updates

After successful provisioning:
- MongoDB password is retrieved from the Kubernetes Secret and updated in the instance configuration file
- The temporary secret containing the MongoDB password is deleted for security

#### 6. ArgoCD Application Creation

Once provisioning is complete, an ArgoCD Application is created to manage the Open edX deployment. The application monitors the cluster repository and deploys the instance when changes are detected.

## Troubleshooting

### Workflow Failures

If a provisioning workflow fails, check the workflow status and logs:

```bash
# Check workflow status
kubectl get workflows -n <instance-name>

# View detailed workflow information
kubectl describe workflow <workflow-name> -n <instance-name>

# View workflow logs
kubectl logs -n <instance-name> workflow/<workflow-name>
```

**Common Issues**:

- **Database Connection Failures**: Verify that database host, port, and credentials are correct
- **Permission Errors**: Ensure admin credentials have sufficient privileges to create databases and users
- **Network Issues**: Check that the Kubernetes cluster can reach the database servers
- **Provider API Errors**: For MongoDB Atlas or DigitalOcean, verify API credentials and permissions

### Partial Provisioning

If provisioning partially succeeds (some workflows succeed, others fail):

1. **Clean Up**: Delete any partially created resources
2. **Check Dependencies**: Ensure all required services (databases, storage) are available
3. **Retry**: Re-run the instance creation process, which will attempt to provision all resources again

### Getting Help

If provisioning continues to fail:

1. **Collect Logs**: Gather workflow logs, Kubernetes events, and any error messages
2. **Check Configuration**: Verify all environment variables and instance configuration values
3. **Check Cluster Health**: Ensure the Kubernetes cluster and Argo Workflows are functioning correctly

## Related Documentation

- [Instances Overview](index.md) -  Instance lifecycle
- [Infrastructure Provisioning](../infrastructure/provisioning.md) -  Cluster and ArgoCD setup
- [Deprovisioning](deprovisioning.md) -  Deleting an instance
- [Configuration](configuration.md) -  Instance config, including Open edX object storage

## See Also

- [Object Storage](configuration.md#object-storage) -  Bucket provisioning vs Tutor S3 plugins
- [Docker Images](docker-images.md) -  Building images after provisioning
- [Infrastructure Overview](../infrastructure/index.md) -  Argo Workflows and provisioning
- [Cluster Authentication](../cluster/authentication.md) -  kubeconfig for running Launchpad CLI
- [Debugging](debugging.md) -  Troubleshooting provisioning issues

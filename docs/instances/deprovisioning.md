# Instance Deprovisioning

Deprovisioning removes all resources associated with an Open edX instance when it is no longer needed. This includes deleting databases, storage buckets, Kubernetes namespaces, and cleaning up RBAC policies. The deprovisioning process is automated through Argo Workflows and executed when deleting an instance.

The deprovisioning system handles:

- **MySQL Database**: Removes database and user
- **MongoDB Database**: Deletes databases and user
- **Storage Buckets**: Deletes S3-compatible storage buckets and their contents
- **Kubernetes Resources**: Removes namespaces, RBAC policies, and service accounts
- **ArgoCD Applications**: Deletes the ArgoCD Application managing the instance

All deprovisioning workflows run in parallel. The process is designed to be idempotent, meaning it can be safely retried if it fails partway through.

## Deprovisioning Steps

### Prerequisites

Before deprovisioning an instance, ensure:

1. **Backup Important Data**: Deprovisioning permanently deletes all instance data. Ensure you have backups if needed
2. **Database Access**: Admin credentials for MySQL and MongoDB servers
3. **Storage Credentials**: Access keys for S3-compatible storage

### Deprovisioning Process

The deprovisioning process is automatically executed when deleting an instance using the `launchpad_delete_instance` command or the GitHub Actions workflow. The process follows these steps:

#### 1. Provision Workflow Cleanup

Any remaining provision workflows are deleted to clean up resources.

#### 2. Deprovision Workflow Creation

Three deprovision workflows are created in parallel:

- **MySQL Deprovision Workflow**: Removes the MySQL database and user
- **MongoDB Deprovision Workflow**: Deletes MongoDB databases and user
- **Storage Deprovision Workflow**: Deletes the storage bucket and its contents

Each workflow is parameterized with instance-specific configuration values extracted from the instance configuration file.

#### 3. Workflow Execution

The workflows execute the following operations:

**MySQL Deprovisioning**:
- Connects to the MySQL server using admin credentials
- Drops the database specified in the instance configuration
- Removes the user associated with the instance
- Cleans up any related permissions

**MongoDB Deprovisioning**:
- Detects the MongoDB provider
- Drops the main database and forum database
- Removes the user associated with the instance
- For API-based providers, uses the provider's API to manage user deletion

**Storage Deprovisioning**:
- Deletes all objects in the storage bucket
- Removes the storage bucket itself
- Uses force deletion to ensure the bucket is removed even if it contains objects

#### 4. Workflow Completion

The system waits for all workflows to complete (default timeout: 300 seconds). Unlike provisioning, deprovisioning workflows that fail are logged as warnings but do not abort the entire process, as some resources may have already been deleted.

#### 5. ArgoCD Application Deletion

The ArgoCD Application managing the instance is deleted. This stops any ongoing deployments and removes the application from ArgoCD.

#### 6. RBAC Cleanup

Cluster-level RBAC resources are removed:
- ClusterRole and ClusterRoleBinding for the instance
- Any other instance-specific RBAC policies

#### 7. Namespace Deletion

The Kubernetes namespace containing all instance resources is deleted. This operation has a timeout of 300 seconds and will remove all remaining resources in the namespace.

#### 8. Instance Directory Removal

The local instance configuration directory is removed from the cluster repository.

### Manual Deprovisioning

If you need to manually trigger deprovisioning workflows, you can use `kubectl`:

```bash
# Apply a deprovision workflow manually
kubectl apply -f <workflow-manifest-url> \
  --namespace <instance-name>

# Monitor workflow status
kubectl get workflows -n <instance-name>

# View workflow logs
kubectl logs -n <instance-name> \
  workflow/<workflow-name>
```

### Force Deletion

If normal deletion fails, you can use the `--force` flag to skip confirmation prompts:

```bash
launchpad_delete_instance <instance-name> --force
```

**Warning**: Force deletion bypasses safety checks and should only be used when you are certain you want to delete the instance.

## Troubleshooting

### Workflow Failures

If a deprovisioning workflow fails, check the workflow status and logs:

```bash
# Check workflow status
kubectl get workflows -n <instance-name>

# View detailed workflow information
kubectl describe workflow <workflow-name> -n <instance-name>

# View workflow logs
kubectl logs -n <instance-name> workflow/<workflow-name>
```

**Common Issues**:

- **Database Connection Failures**: Verify that database host, port, and credentials are still valid
- **Resource Already Deleted**: Some workflows may fail if resources were already deleted. This is expected and typically safe to ignore
- **Permission Errors**: Ensure admin credentials have sufficient privileges to delete databases and users
- **Provider API Errors**: For MongoDB Atlas or DigitalOcean, verify API credentials are still valid

### Namespace Stuck in Terminating State

If a namespace is stuck in the "Terminating" state:

1. **Check for Finalizers**: Some resources may have finalizers preventing deletion
   ```bash
   kubectl get namespace <instance-name> -o yaml
   ```

2. **Force Remove Finalizers**: If safe, you can manually remove finalizers:
   ```bash
   kubectl patch namespace <instance-name> \
     -p '{"metadata":{"finalizers":[]}}' \
     --type=merge
   ```

3. **Check Remaining Resources**: List resources that may be preventing deletion:
   ```bash
   kubectl api-resources --verbs=list --namespaced -o name | \
     xargs -n 1 kubectl get --show-kind --ignore-not-found -n <instance-name>
   ```

### Partial Deprovisioning

If deprovisioning partially succeeds (some resources deleted, others remain):

1. **Identify Remaining Resources**: Check what resources still exist
2. **Manual Cleanup**: Manually delete remaining resources if safe to do so
3. **Retry Workflows**: Re-run the deprovision workflows for failed components

### Database Deletion Issues

If databases cannot be deleted:

- **MySQL**: Ensure no active connections to the database. You may need to manually drop the database:
  ```sql
  DROP DATABASE IF EXISTS <database-name>;
  DROP USER IF EXISTS '<username>'@'%';
  ```

- **MongoDB**: For API-based providers, check provider-specific limitations. Some providers may require manual cleanup through their web interface

### Storage Bucket Deletion Issues

If storage buckets cannot be deleted:

- **Non-Empty Buckets**: Ensure all objects are deleted before deleting the bucket. The deprovision workflow uses force deletion, but some providers may have additional requirements
- **Bucket Policies**: Check if bucket policies or lifecycle rules are preventing deletion
- **Manual Cleanup**: You may need to manually delete the bucket through the provider's console if the workflow fails

### ArgoCD Application Issues

If the ArgoCD Application cannot be deleted:

```bash
# Check application status
kubectl get application -n argocd <application-name>

# Force delete if necessary
kubectl delete application <application-name> -n argocd --force --grace-period=0
```

### RBAC Cleanup Issues

If RBAC resources cannot be deleted:

```bash
# List remaining RBAC resources
kubectl get clusterrole | grep <instance-name>
kubectl get clusterrolebinding | grep <instance-name>

# Manually delete if needed
kubectl delete clusterrole <instance-name>-workflows
kubectl delete clusterrolebinding <instance-name>-binding
```

### Workflow Timeout

If workflows are timing out:

1. **Check Resource State**: Verify that resources are in a state that allows deletion
2. **Increase Timeout**: The default timeout is 300 seconds. For large databases or buckets with many objects, this may need to be increased
3. **Manual Intervention**: If workflows consistently timeout, consider manually deleting resources and then cleaning up the workflows

### Data Recovery

If you need to recover data after deprovisioning:

- **Backups**: Check if backups were created before deprovisioning (if Velero backup solutions are configured)
- **Database Snapshots**: Some database providers maintain snapshots that can be restored
- **Storage Buckets**: If the bucket was not force-deleted, objects may still be recoverable depending on the provider's retention policies

**Note**: Once deprovisioning is complete, data recovery may not be possible. Always ensure backups are created before deprovisioning production instances.

### Getting Help

If deprovisioning continues to fail:

1. **Collect Logs**: Gather workflow logs, Kubernetes events, and any error messages
2. **Check Resource State**: Verify the current state of databases, storage, and Kubernetes resources
3. **Review Configuration**: Ensure all environment variables and credentials are still valid
4. **Manual Cleanup**: As a last resort, manually clean up remaining resources following provider-specific procedures

## Related Documentation

- [Instances Overview](index.md) -  Instance lifecycle
- [Provisioning](provisioning.md) -  What gets created for an instance
- [Infrastructure Deprovisioning](../infrastructure/deprovisioning.md) -  Cluster-level deprovisioning
- [Cluster Backup](../cluster/backup.md) -  Backing up before deprovisioning

## See Also

- [Configuration](configuration.md) -  Instance config and credentials
- [Infrastructure Overview](../infrastructure/index.md) -  Argo Workflows and resources
- [Cluster Restore](../cluster/restore.md) -  Restore procedures
- [Debugging](debugging.md) -  Troubleshooting deprovisioning issues

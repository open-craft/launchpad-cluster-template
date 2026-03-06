# Infrastructure Deprovisioning

Deprovisioning is removing the Kubernetes cluster and all associated resources when they are no longer needed. This includes uninstalling GitOps tools (ArgoCD and Argo Workflows), destroying infrastructure resources, and cleaning up configuration files.

The deprovisioning process should be performed in reverse order of provisioning:

1. **Remove All Instances**: Delete all Open edX instances first
2. **Uninstall GitOps Tools**: Remove ArgoCD and Argo Workflows
3. **Destroy Infrastructure**: Destroy Kubernetes cluster and supporting resources using Terraform/OpenTofu
4. **Clean Up Configuration**: Remove local cluster configuration files

**Warning**: Deprovisioning is a destructive operation that permanently removes all resources and data. Ensure you have backups of any important data before proceeding.

## Prerequisites

Before deprovisioning infrastructure, ensure:

- **All Instances Removed**: All Open edX instances have been deleted
- **Backups Verified**: Any required backups have been created and verified
- **Access Credentials**: Valid credentials for cloud provider and Kubernetes cluster
- **Terraform/OpenTofu State**: Access to Terraform state file (for infrastructure destruction)

## Deprovisioning Steps

### Step 1: Verify No Active Instances

Before deprovisioning infrastructure, ensure all Open edX instances have been removed:

```bash
# List all namespaces (excluding system namespaces)
kubectl get namespaces --field-selector metadata.name!=kube-system,metadata.name!=kube-public,metadata.name!=kube-node-lease

# Check for ArgoCD applications
kubectl get applications -n argocd

# Verify no instance namespaces exist
kubectl get namespaces | grep -v "kube-\|argocd\|argo\|default"
```

If any instances remain, delete them first using `launchpad_delete_instance`, the GitHub Actions workflow, or manually.

### Step 2: Uninstall ArgoCD and Argo Workflows

Remove the GitOps tools from the cluster. While there's no dedicated uninstall command, you can remove them manually:

**Uninstall ArgoCD**:

```bash
# Delete ArgoCD namespace (this removes all ArgoCD resources)
kubectl delete namespace argocd

# Wait for namespace to be fully deleted
kubectl wait --for=delete namespace/argocd --timeout=300s
```

**Uninstall Argo Workflows**:

```bash
# Delete workflow templates first
kubectl delete clusterworkflowtemplates --all

# Delete Argo Workflows namespace
kubectl delete namespace argo

# Wait for namespace to be fully deleted
kubectl wait --for=delete namespace/argo --timeout=300s
```

**Verify Removal**:

```bash
# Verify namespaces are gone
kubectl get namespace argocd  # Should return "not found"
kubectl get namespace argo    # Should return "not found"

# Verify no ArgoCD resources remain
kubectl get all -n argocd  # Should return "not found"

# Verify no Argo Workflows resources remain
kubectl get all -n argo  # Should return "not found"
```

**Note**: If namespaces are stuck in "Terminating" state, see the [Troubleshooting](#namespace-stuck-in-terminating-state) section.

### Step 3: Clean Up Remaining Resources

Remove any remaining resources that might prevent infrastructure destruction:

We are listing the PVs and PVCs in order to keep a record of what was used by the cluster. In case the cluster deletion goes sideways, we have easier job identifying dangling resources.

```bash
# List persistent volumes
kubectl get pv

# List persistent volume claims
kubectl get pvc --all-namespaces

# List storage classes
kubectl get storageclass

# List custom resource definitions
kubectl get crd
```

**Delete selective resources** (replace `<name>` and `<namespace>` with actual values):

```bash
# Delete a persistent volume claim (typically required before deleting its bound PV)
kubectl delete pvc <pvc-name> -n <namespace>

# Delete a persistent volume
kubectl delete pv <pv-name>

# Delete a storage class (only if not in use)
kubectl delete storageclass <storageclass-name>

# Delete a custom resource definition (removes the CRD and all instances of that resource)
kubectl delete crd <crd-name>
```

**Remove Custom Resources** (if needed):

```bash
# Remove ArgoCD CRDs (if not removed with namespace)
kubectl delete crd applications.argoproj.io
kubectl delete crd application sets.argoproj.io
kubectl delete crd appprojects.argoproj.io

# Remove Argo Workflows CRDs (if not removed with namespace)
kubectl delete crd clusterworkflowtemplates.argoproj.io
kubectl delete crd cronworkflows.argoproj.io
kubectl delete crd workflows.argoproj.io
kubectl delete crd workflowtemplates.argoproj.io
kubectl delete crd workfloweventbindings.argoproj.io
```

### Step 4: Destroy Infrastructure

Destroy the infrastructure using Terraform or OpenTofu. This will remove the Kubernetes cluster and all associated cloud resources.

**Navigate to Infrastructure Directory**:

```bash
cd launchpad-production-cluster/infrastructure-aws  # or infrastructure-digitalocean
```

**Configure Backend Credentials**:

See the [provisioning](provisioning.md) guide on how to setup the backend credentials.

**Review Destruction Plan**:

```bash
# Review what will be destroyed
tofu plan -destroy
```

**Destroy Infrastructure**:

```bash
# Destroy all infrastructure
tofu destroy
```

**What Gets Destroyed**:

- **Kubernetes Cluster**: EKS or DOKS cluster
- **Node Groups**: All worker nodes
- **Databases**: Managed MySQL and MongoDB instances
- **Storage**: S3 buckets or DigitalOcean Spaces
- **Networking**: Load balancers, VPC resources (depending on configuration)
- **Other Resources**: Any other resources created by Terraform modules

**Important Notes**:

- Some resources may take time to destroy (especially databases and storage)
- External databases and storage will be destroyed
- Review the destruction plan carefully before confirming

### Step 5: Clean Up Local Configuration

After infrastructure is destroyed, you can optionally remove local cluster configuration:

**Remove Cluster Directory**:

```bash
# Navigate to parent directory
cd ../..

# Remove cluster configuration directory
rm -rf launchpad-production-cluster
```

**Remove kubeconfig**:

```bash
# Remove cluster-specific kubeconfig
rm ~/.kube/config-cluster

# Or remove from main kubeconfig if merged
kubectl config delete-context <cluster-context-name>
kubectl config delete-cluster <cluster-name>
```

**Note**: You may want to keep the cluster configuration directory for reference or to recreate the cluster later.

## Troubleshooting

### Namespace Stuck in Terminating State

If ArgoCD or Argo Workflows namespaces are stuck in "Terminating" state:

**Check for Blocking Resources**:

```bash
# List all resources in the namespace
kubectl api-resources --verbs=list --namespaced -o name | \
  xargs -n 1 kubectl get --show-kind --ignore-not-found -n argocd

# Check for finalizers
kubectl get namespace argocd -o yaml | grep finalizers
```

**Force Remove Finalizers**:

```bash
# Edit namespace to remove finalizers
kubectl patch namespace argocd \
  -p '{"metadata":{"finalizers":[]}}' \
  --type=merge
```

**Force Delete Resources**:

If specific resources are blocking deletion:

```bash
# Find resources with finalizers
kubectl get all -n argocd -o yaml | grep -A 5 finalizers

# Remove finalizers from specific resource
kubectl patch <resource-type> <resource-name> -n argocd \
  -p '{"metadata":{"finalizers":[]}}' \
  --type=merge
```

### Infrastructure Destruction Issues

**Terraform/OpenTofu Errors**:

- **State Lock**: If state is locked, check for other running Terraform processes
- **Resource Dependencies**: Some resources may have dependencies preventing deletion
- **Provider Timeouts**: Large resources may take longer than default timeouts

**Common Solutions**:

```bash
# Force unlock state (use with caution)
tofu force-unlock <lock-id>

# Destroy specific resources first
tofu destroy -target=<resource-address>

# Increase timeout for slow resources
export TF_CLI_ARGS="-timeout=30m"
tofu destroy
```

**Resources Not Destroyed**:

Some resources may not be destroyed if:

- They're managed outside of Terraform
- They have deletion protection enabled
- They're shared resources used by other clusters

Manually remove these resources through the cloud provider console if needed.

### Kubernetes Cluster Access Issues

**Cannot Access Cluster During Destruction**:

- If the cluster API server is already destroyed, you cannot use `kubectl` commands
- Some resources may be destroyed automatically by the cloud provider
- Check cloud provider console for remaining resources

**Orphaned Resources**:

After cluster destruction, some resources may remain:

- Load balancers
- Persistent volumes (if not properly cleaned up)
- Security groups
- IAM roles and policies

Manually clean these up through the cloud provider console.

### State File Issues

**State File Not Found**:

- Verify backend configuration is correct
- Check that state file exists in the backend storage
- Ensure backend credentials have read access

**State File Corruption**:

```bash
# Backup state file first
tofu state pull > state-backup.json

# Try to refresh state
tofu refresh

# If refresh fails, you may need to import resources or recreate state
```

### Partial Destruction

If destruction partially succeeds:

1. **Review Remaining Resources**: Check what resources still exist
2. **Manual Cleanup**: Remove remaining resources through cloud provider console
3. **Update State**: Use `tofu state rm` to remove destroyed resources from state
4. **Retry Destruction**: Run `tofu destroy` again to clean up remaining resources

### Data Recovery

If you need to recover data after deprovisioning:

- **Backups**: Check if Velero or other backup solutions created backups
- **Database Snapshots**: Some cloud providers maintain database snapshots
- **Storage Buckets**: If buckets weren't destroyed, data may still be accessible
- **Volume Snapshots**: Check for volume snapshots in your cloud provider

**Note**: Recovery may not be possible if backups weren't configured or have been deleted.

## Best Practices

### Before Deprovisioning

1. **Create Backups**: Ensure all important data is backed up
2. **Document Configuration**: Save cluster configuration for future reference
3. **Verify Dependencies**: Check that no other systems depend on this infrastructure

### During Deprovisioning

1. **Follow Order**: Remove instances → Uninstall tools → Destroy infrastructure
2. **Monitor Progress**: Watch for errors and address them promptly
3. **Verify Removal**: Confirm resources are actually destroyed, not just marked for deletion
4. **Keep Logs**: Save logs of the deprovisioning process for troubleshooting

### After Deprovisioning

1. **Verify Cleanup**: Check cloud provider console for any remaining resources
2. **Update Documentation**: Note that infrastructure has been deprovisioned
3. **Archive Configuration**: Keep cluster configuration in version control for reference
4. **Review Costs**: Verify that cloud provider billing reflects the destroyed resources

## Next Steps

After successfully deprovisioning infrastructure:

1. **Verify Billing**: Confirm cloud provider billing reflects destroyed resources
2. **Archive Configuration**: Keep cluster configuration for future reference
3. **Update Documentation**: Document that the cluster has been deprovisioned
4. **Clean Up Credentials**: Rotate or remove any credentials that were used for this cluster

## Related Documentation

- [Infrastructure Overview](index.md) -  Core components and architecture
- [Provisioning](provisioning.md) -  How infrastructure is provisioned
- [Cluster Overview](../cluster/index.md) -  Cluster operations
- [Instance Deprovisioning](../instances/deprovisioning.md) -  Deleting Open edX instances

## See Also

- [Cluster Backup](../cluster/backup.md) -  Backup before deprovisioning
- [Cluster Restore](../cluster/restore.md) -  Restore procedures
- [Custom Resources](custom-resources.md) -  Resources removed during deprovisioning

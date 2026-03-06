# Instance Debugging

This page summarizes common issues and debugging steps for Open edX instances on the cluster.

## Pod Not Starting or Crashing

1. **Describe the pod** -  `kubectl describe pod -n <instance-name> <pod-name>` for events, restarts, and probe failures.
2. **Logs** -  `kubectl logs -n <instance-name> <pod-name> --previous` if the container has restarted.
3. **Image pull** -  Ensure the image exists in the registry and that `imagePullSecrets` are set (Launchpad configures registry credentials for the namespace).
4. **Init jobs** -  Drydock init jobs (e.g. migrations) run before the main app; check init container logs if the main container never starts.

## ArgoCD Out of Sync

- In ArgoCD UI, check the application status and diff.
- Common causes: manifest errors, missing ConfigMaps/Secrets, or source repo not updated.
- Fix manifests in the cluster repo and sync, or resolve reported errors (e.g. missing image, wrong namespace).

## Database or Storage Connectivity

- Verify Secrets in the instance namespace contain the correct credentials (e.g. MySQL, MongoDB, S3).
- Check that provision workflows completed and that the instance config (and Tutor env) point to the right hosts and bucket names.
- Test connectivity from a pod: `kubectl exec -n <instance-name> <pod-name> -- ...` and run a simple client (e.g. `mysql`, `mongosh`) or curl to the storage endpoint.

## Image Not Found or Pull Errors

- Confirm the image name and tag in `config.yml` match what was built and pushed (e.g. by Picasso).
- Ensure the namespace has the correct `imagePullSecrets` (Launchpad sets this on instance creation and during `launchpad_install_argo`).
- Check registry credentials (e.g. `LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS`) in the environment that created the instance or runs the workflows.

## Slow or Failing Sync

- Check ArgoCD application sync status and any error messages.
- Ensure the source path in the Application manifest exists and has valid Kubernetes YAML.
- For large repos, sync can take longer; check ArgoCD logs if needed.

## Getting More Help

- Collect: `kubectl describe` and `kubectl logs` for failing pods, ArgoCD application status, and relevant config snippets.
- See [Provisioning](provisioning.md) and [Deprovisioning](deprovisioning.md) for workflow-related issues.
- See [Configuration](configuration.md) for config and secrets.

## Related Documentation

- [Instances Overview](index.md) -  Instance lifecycle
- [Provisioning](provisioning.md) -  Instance creation and workflows
- [Deprovisioning](deprovisioning.md) -  Instance deletion and cleanup
- [Configuration](configuration.md) -  Config and secrets

## See Also

- [Tracking Logs](tracking-logs.md) -  Viewing pod logs
- [Instance Monitoring](monitoring.md) -  Metrics and health
- [Infrastructure Overview](../infrastructure/index.md) -  ArgoCD and Argo Workflows
- [User Guides Overview](../user-guides/index.md) -  Task-based guides

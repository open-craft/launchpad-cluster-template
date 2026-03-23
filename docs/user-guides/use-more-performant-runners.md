# Use More Performant Runners

This guide describes how to use higher-performance runners for your build and build-all GitHub Actions. OpenCraft uses [Blacksmith](https://blacksmith.sh/), a drop-in replacement for GitHub-hosted runners.

## Prerequisites

- The [Blacksmith GitHub App](https://github.com/apps/blacksmith-sh) must be installed for your GitHub organization. Blacksmith is available for organizations only, not personal repositories.
- Your cluster must have been created from the Launchpad cluster template with the build workflows.

## Changing the Runner Label

The build and build-all workflows use a `RUNNER_WORKFLOW_LABEL` input that controls which runner executes the jobs. By default, clusters use `ubuntu-latest` (GitHub-hosted runners). To use Blacksmith, set the label to a Blacksmith runner tag such as `blacksmith-8vcpu-ubuntu-2404`. We use `blacksmith-8vcpu-ubuntu-2404` as it provides a reasonably fast build for the MFE and platform as well.

### Option 1: Set Default When Creating a New Cluster

When generating a new cluster with cookiecutter, choose a Blacksmith runner for `runner_workflow_label` instead of `ubuntu-latest`, use the runner label you wish to use.

### Option 2: Edit Workflow Defaults in Your Cluster Repository

For existing clusters, edit the workflow files in your cluster repository to change the default value of `RUNNER_WORKFLOW_LABEL`:

1. In your cluster repo (e.g. `open-craft/launchpad-my-cluster`), open `.github/workflows/build.yml` and `.github/workflows/build-all.yml`.

2. Change the default for the `RUNNER_WORKFLOW_LABEL` input from `ubuntu-latest` (or `self-hosted`) to a Blacksmith runner tag, for example:

   ```yaml
   RUNNER_WORKFLOW_LABEL:
     description: 'The label of the runner workflow to run'
     required: false
     default: "blacksmith-8vcpu-ubuntu-2404"  # Blacksmith: 8 vCPU, 32 GB, Ubuntu 24.04
     type: string
   ```

3. Commit and push. All future build and build-all runs will use Blacksmith unless overridden when manually triggering a workflow.

### Option 3: Override When Manually Triggering

When you run the **Build** or **Build All Images** workflow from the GitHub Actions UI (workflow_dispatch), you can override the runner label by changing the `RUNNER_WORKFLOW_LABEL` input to `blacksmith-8vcpu-ubuntu-2404` (or another Blacksmith tag) before starting the run. This does not require editing any files.

## Blacksmith Runner Tags (OpenCraft Example)

OpenCraft typically uses the following Blacksmith runners for Docker builds:

| Runner Tag                         | vCPU | Memory | Use Case                      |
| --------------------------------- | ---- | ------ | ----------------------------- |
| `blacksmith-2vcpu-ubuntu-2404`     | 2    | 8 GB   | Quick, light builds            |
| `blacksmith-8vcpu-ubuntu-2404`     | 4    | 16 GB  | Standard Open edX image builds |
| `blacksmith-8vcpu-ubuntu-2404`     | 8    | 32 GB  | Faster builds, heavier images  |
| `blacksmith-16vcpu-ubuntu-2404`    | 16   | 64 GB  | Large or parallelized builds   |

For Ubuntu 22.04, use the `ubuntu-2204` variants (e.g. `blacksmith-4vcpu-ubuntu-2204`). See the [Blacksmith Instance Types](https://docs.blacksmith.sh/blacksmith-runners/overview) documentation for the full list.

## Other Workflows Using Runners

The `create-instance`, `update-instance`, and `delete-instance` workflows also accept `RUNNER_WORKFLOW_LABEL`. If you want those to use Blacksmith as well, edit their defaults in your cluster repo in the same way as for build and build-all.

## Related Documentation

- [User Guides Overview](index.md) - All user guides
- [Instance Provisioning](../instances/provisioning.md) - Instance creation and builds
- [Instance Configuration](../instances/configuration.md) - Instance manifests

## See Also

- [Blacksmith Documentation](https://docs.blacksmith.sh/) - Runner types, pricing, setup
- [Pull Request Sandboxes](pull-request-sandboxes.md) - Sandbox environments for PRs

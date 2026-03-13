# {{ cookiecutter.cluster_name }}

{% if cookiecutter.short_description -%}
> {{ cookiecutter.short_description }}
{%- endif %}

This repository serves as the home for the {{ cookiecutter.cluster_name }} cluster. All the necessary infrastructure, cluster, and instance configuration are living in this repository.

## Infrastructure Setup

This cluster uses Terraform/OpenTofu with S3-compatible backends for state storage. Backend credentials suggested to be provided **via backend.hcl** to avoid storing sensitive information in state files.

The backend uses a `tfstate-launchpad-{{ cookiecutter.cluster_slug_normalized }}-cluster-{{ cookiecutter.environment }}` bucket to store its state. Make sure the bucket exists before applying changes. Also, ensure the user the Access Key belongs to has access to the bucket.

Create a new `backend.hcl` file in the infrastructure directory:

```hcl
access_key = "<ACCESS KEY ID>"
secret_key = "<SECRET ACCESS KEY>"
```

### Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure-{{ cookiecutter.cloud_provider }}

# Initialize and deploy
tofu init
tofu plan
tofu apply
```

## Repository Setup

This repo uses [pre-commit](https://pre-commit.com/) to ensure the code is formatted and up to standards before it is being committed.

Once pre-commit is installed, execute `pre-commit install` to setup the git commit hooks. Then, execute `pre-commit install -t commit-msg` to allow the `commit-msg` state.

## Commit messages

Commit messages are enforced by `pre-commit` and must conform the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) style. On top of that, the repository mandates to include a JIRA ticket in the commit message.

To do so, commit your changes like `git commit -m "feat: add new instance config" -m "TASK-1234"` where `TASK-1234` is the ticket number. This will ensure the ticket number is not in the first line, but the commit still contains it.

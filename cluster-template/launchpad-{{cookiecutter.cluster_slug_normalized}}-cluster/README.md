# {{ cookiecutter.cluster_name }}

{% if cookiecutter.short_description -%}
> {{ cookiecutter.short_description }}
{%- endif %}

This repository serves as the home for the {{ cookiecutter.cluster_name }} cluster. All the necessary infrastructure, cluster, and instance configuration are living in this repository.

## Infrastructure Setup

This cluster uses Terraform/OpenTofu with S3-compatible backends for state storage. Backend credentials are provided **via backend.hcl** so they are not stored in the repository.

The backend uses a `tfstate-launchpad-{{ cookiecutter.cluster_slug_normalized }}-cluster-{{ cookiecutter.environment }}` bucket. Create that bucket before `tofu init`. The access key must be allowed to read and write the bucket.

{% if cookiecutter.cloud_provider == "upcloud" -%}
UpCloud Managed Object Storage hostnames are created with the storage service (`https://<service-id>.upcloudobjects.com`) and are not derived from the zone. Put the connection in `infrastructure/backend.hcl`:

```hcl
endpoints = {
  s3 = "https://<service-id>.upcloudobjects.com"
}

bucket     = "tfstate-launchpad-{{ cookiecutter.cluster_slug_normalized }}-cluster-{{ cookiecutter.environment }}"
region     = "<object storage region>"
access_key = "<ACCESS KEY ID>"
secret_key = "<SECRET ACCESS KEY>"
```

Zone `us-nyc1` uses object storage region `us-1`. Zone `de-fra1` uses `europe-1`. Set `object_storage_region_override` in `config.tf` to `europe-2` or `europe-3` to override that European default. Set `atlas_project_id` in `config.tf`. `atlas_region_name` follows the zone: `US_EAST_1` for US zones, `EU_CENTRAL_1` for European zones, `AP_SOUTHEAST_2` for `au-syd1`, and `AP_SOUTHEAST_1` for `sg-sin1`. Set `atlas_public_key` and `atlas_private_key` in `secrets.auto.tfvars`. `atlas_public_key` and `atlas_private_key` may be omitted when `MONGODB_ATLAS_PUBLIC_KEY` and `MONGODB_ATLAS_PRIVATE_KEY` are set.
{% else -%}
Create `infrastructure/backend.hcl`:

```hcl
access_key = "<ACCESS KEY ID>"
secret_key = "<SECRET ACCESS KEY>"
```
{% if cookiecutter.cloud_provider == "aws" %}
MySQL is Amazon RDS in the private subnets, while MongoDB is a MongoDB Atlas cluster peered to the VPC, with routes on the private route tables. Set `atlas_project_id` in `config.tf`. Set `atlas_public_key` and `atlas_private_key` in `secrets.auto.tfvars`. The peered CIDR is `atlas_cidr_block` in `config.tf` and must not overlap the VPC. `atlas_public_key` and `atlas_private_key` may be omitted when `MONGODB_ATLAS_PUBLIC_KEY` and `MONGODB_ATLAS_PRIVATE_KEY` are set. The Atlas region is the AWS region with hyphens replaced by underscores and uppercased. The AWS keys in `secrets.auto.tfvars` are also used for Velero, so they must be allowed to use the backup bucket and its KMS key. `.kubeconfig` calls `aws eks get-token` and does not store those keys. `kubectl` needs the AWS CLI and credentials that can access the cluster.
{% endif %}
{% endif %}

### Deploy Infrastructure

```bash
cd infrastructure
tofu init -backend-config=backend.hcl
tofu plan
tofu apply
```

## Repository Setup

This repo uses [pre-commit](https://pre-commit.com/) to ensure the code is formatted and up to standards before it is being committed.

Once pre-commit is installed, execute `pre-commit install` to setup the git commit hooks. Then, execute `pre-commit install -t commit-msg` to allow the `commit-msg` state.

## Commit messages

Commit messages are enforced by `pre-commit` and must conform the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) style. On top of that, the repository mandates to include a JIRA ticket in the commit message.

To do so, commit your changes like `git commit -m "feat: add new instance config" -m "TASK-1234"` where `TASK-1234` is the ticket number. This will ensure the ticket number is not in the first line, but the commit still contains it.

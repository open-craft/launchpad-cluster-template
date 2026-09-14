# Proposal: consolidate configuration for the `launchpad_*` commands

POC implemented on `launchpad_install_argo` only. The rest of the `launchpad_*` commands were not touched. We can delete this file once an approach is approved.

## The problem

The `launchpad_*` commands mix CLI arguments and `LAUNCHPAD_*` environment variables for the same configuration, without documenting it in `--help`, and validate late. In `launchpad_install_argo`, for example, enabling SSO without credentials only failed inside `_configure_argocd_github_sso` — **after** creating the `argocd` namespace and applying several manifests. There was also a function (`_build_argocd_sso_cli_overrides`) dedicated solely to manually merging CLI and env vars for 4 fields — a pattern that doesn't scale.

## The proposal

Use `pydantic-settings` (already a project dependency) so each command has **a single configuration class** instead of `argparse` + manual env var reading:

- **Automatic precedence:** CLI > `LAUNCHPAD_*` env var > default.
- **Auto-generated `--help`**, showing each option's env var without maintaining that text by hand.
- **Eager validation:** invalid config (e.g. SSO enabled without credentials) fails when the object is constructed, **before** touching Kubernetes.

## Before / after

**Validation:** before, enabling SSO without credentials failed halfway through the install, with the `argocd` namespace and several manifests already applied to the cluster. Now, the same error is caught as soon as the command starts, before even trying to connect to the cluster — nothing gets created or modified.

**`main()`:** before, it had ~55 lines building the `argparse` parser and manually merging values coming from the CLI with values coming from env vars. Now it's reduced to: build the configuration (fails right there if invalid), and if valid, install ArgoCD and Argo Workflows — the parsing, precedence, and validation logic now lives in the configuration class, not repeated in each command.

## Field reuse

For different commands to share fields (e.g. `cluster_domain`) without duplicating their declaration or dragging in fields they don't use, each field lives in a single-field `BaseModel` mixin (`launchpad/config.py`), and each configuration class composes only the ones it needs:

```python
class DockerRegistryField(BaseModel):
    docker_registry: str = Field(default="ghcr.io", ...)

class ArgoInstallSettings(LaunchpadBaseSettings, DockerRegistryField, ...):
    ...
```

Fine-grained (one mixin per field, not grouped by topic) so that "compose only what I need" is always true.

## Discarded ideas

- **Inheriting `ClusterConfig` in full** instead of composing mixins. It would bring in fields `launchpad_install_argo` doesn't use (e.g. `instances_directory`, `environment`), cluttering its `--help` with options that don't apply.
- **Mixins grouped by topic** (e.g. a single `DockerRegistryFields` with `docker_registry` and `docker_registry_credentials` together). A future command that only needs one of the two fields would still end up dragging in the other — the same problem as inheriting all of `ClusterConfig`, at a smaller scale.
- **A configuration file (`launchpad.yaml`)** as an additional source. Today there would be nothing real to migrate to that file (env vars remain the actual source of truth), so adding it without a concrete use case doesn't demonstrate anything in this POC.

## Checklist against the original issue

The issue listed 4 improvement ideas. Status after this POC:

1. **More comprehensive `--help`** (defaults, env vars, docs link): Done.
2. **Consolidate configuration** (e.g. pick a single source: all args, all env vars, or all a toml/yaml file): Partial. The *code* is consolidated into one settings class with clear precedence, but the command still accepts two sources (CLI + env var), not a single exclusive one as the issue's example suggests.
3. **Stop using env vars altogether** — Not done. `LAUNCHPAD_*` still works exactly as before, kept for backward compatibility.
4. **Validate config with something like Pydantic** — Done. Eager validation before touching the cluster.

Items 2 and 3 are related: picking a single configuration source (dropping env vars, or dropping CLI args, or moving to a config file) is a bigger decision than this POC's scope. 

## What does NOT change

- The `LAUNCHPAD_*` env vars keep working exactly the same, none are deprecated.
- Same external behavior of the command (same flags, same defaults).
- No other command was touched for now.

## Next Steps

- If this proposal is accepted, it can be implemented in the other commands without any regression.
- Hold a discussion to make a decision regarding the points that still need to be resolved:
    - Consolidate configuration (sources)
    - Stop using env vars altogether

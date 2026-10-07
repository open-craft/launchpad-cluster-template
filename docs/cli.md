# Launchpad CLI

The Launchpad stack is designed to be driven via Github Actions. However, it can be convenient to do certain things in a local machine. The Launchpad CLI is useful in such usecases.

## Prerequisites

* [uv](https://docs.astral.sh/uv/)

## Installation

Install Launchpad CLI as an uv tool

```sh
uv tool install git+https://github.com/open-craft/launchpad-cluster-template.git#subdirectory=tooling
```

Or run one-off commands without installing

```sh
uvx --from git+https://github.com/open-craft/launchpad-cluster-template.git#subdirectory=tooling launchpad_create_cluster --help
```

More information about available commands and features can be found in the [tooling README](https://github.com/open-craft/launchpad-cluster-template/tree/main/tooling).

# Enabling ArgoCD GitHub SSO

This guide explains how to enable GitHub SSO for ArgoCD using the bundled Dex
server. It covers both a fresh ArgoCD installation and an existing installation.

## Prerequisites

Create a GitHub OAuth App with these values:

- **Homepage URL**: `https://argocd.<cluster-domain>`
- **Authorization callback URL**: `https://argocd.<cluster-domain>/api/dex/callback`

Keep the OAuth client ID and client secret available for the install or patch
commands below.

Use the GitHub organization slugs that should be allowed to sign in. For example,
`open-craft` allows members of the `open-craft` GitHub organization to
authenticate. Authorization is still handled separately by ArgoCD RBAC.

## New ArgoCD Installation

Use this path when ArgoCD is not installed yet, or when you are intentionally
re-running the Launchpad ArgoCD installer.

```bash
set -euo pipefail

export LAUNCHPAD_CLUSTER_DOMAIN="prod.opencraft.hosting"
export LAUNCHPAD_DOCKER_REGISTRY_CREDENTIALS="base64 encoded docker registry credentials"

launchpad_install_argo --argocd-only \
  --enable-argocd-github-sso \
  --argocd-github-oauth-client-id "github-oauth-client-id" \
  --argocd-github-oauth-client-secret "github-oauth-client-secret" \
  --argocd-github-orgs "open-craft"
```

If you are installing both ArgoCD and Argo Workflows, omit `--argocd-only`:

```bash
set -euo pipefail

launchpad_install_argo \
  --enable-argocd-github-sso \
  --argocd-github-oauth-client-id "github-oauth-client-id" \
  --argocd-github-oauth-client-secret "github-oauth-client-secret" \
  --argocd-github-orgs "open-craft"
```

The installer configures:

- `argocd-cm` with `url: https://argocd.<cluster-domain>`
- `argocd-cm` with a Dex GitHub connector
- `argocd-secret` with `dex.github.clientSecret`

Restart the ArgoCD Dex and server pods after the install:

```bash
set -euo pipefail

kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-dex-server
kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server
```

## Existing ArgoCD Installation

Use this path when ArgoCD is already installed and you want to configure SSO
without replacing the cluster.

### Option 1: Re-run the Launchpad ArgoCD installer

This is the preferred path when you have the current Launchpad tooling available.

```bash
set -euo pipefail

export LAUNCHPAD_CLUSTER_DOMAIN="prod.opencraft.hosting"

launchpad_install_argo --argocd-only \
  --enable-argocd-github-sso \
  --argocd-github-oauth-client-id "github-oauth-client-id" \
  --argocd-github-oauth-client-secret "github-oauth-client-secret" \
  --argocd-github-orgs "open-craft"
```

### Option 2: Patch Kubernetes resources manually

Use direct `kubectl` patches if you cannot re-run the Launchpad installer.

```bash
set -euo pipefail

export LAUNCHPAD_CLUSTER_DOMAIN="prod.opencraft.hosting"
export LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_ID="github-oauth-client-id"
export LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_SECRET="github-oauth-client-secret"
export LAUNCHPAD_ARGOCD_GITHUB_ORGS="open-craft"

kubectl patch configmap argocd-cm \
  -n argocd \
  --type merge \
  --patch-file /dev/stdin <<EOF
data:
  url: "https://argocd.${LAUNCHPAD_CLUSTER_DOMAIN}"
  dex.config: |
    connectors:
    - type: github
      id: github
      name: GitHub
      config:
        clientID: ${LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_ID}
        clientSecret: \$dex.github.clientSecret
        orgs:
        - name: ${LAUNCHPAD_ARGOCD_GITHUB_ORGS}
EOF

kubectl patch secret argocd-secret \
  -n argocd \
  --type merge \
  --patch-file /dev/stdin <<EOF
stringData:
  dex.github.clientSecret: "${LAUNCHPAD_ARGOCD_GITHUB_OAUTH_CLIENT_SECRET}"
EOF
```

If you allow multiple GitHub organizations, patch `dex.config` with one
`- name: <org-slug>` entry per organization:

```yaml
orgs:
- name: open-craft
- name: another-org
```

### Patch the ingress

The ArgoCD ingress must not use `nginx.ingress.kubernetes.io/app-root: /login`
with SSO. That nginx redirect can send the browser back to the login page after
Dex reports a successful login.

Remove the annotation from an existing ingress:

```bash
set -euo pipefail

kubectl annotate ingress argocd-server-ingress \
  -n argocd \
  nginx.ingress.kubernetes.io/app-root- \
  --overwrite
```

Confirm it is gone:

```bash
set -euo pipefail

kubectl get ingress argocd-server-ingress \
  -n argocd \
  -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/app-root}{"\n"}'
```

The command should print an empty line.

### Restart ArgoCD

Restart Dex and the ArgoCD API server after changing SSO settings:

```bash
set -euo pipefail

kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-dex-server
kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server
```

Hard-refresh the browser or clear site data for the ArgoCD host before testing
the login flow again.

## Configure RBAC

GitHub SSO authenticates the user; ArgoCD RBAC decides what the user can do.
The default Launchpad RBAC policy grants `role:readonly` by default.

Map GitHub users or groups in `argocd-rbac-cm`. If you manage RBAC from
manifests, prefer updating `manifests/argocd-rbac-config.yml` or your
cluster-specific overlay instead of patching the live ConfigMap.

For example, if Dex reports the group claim `open-craft:Core`, add this line to
the existing `policy.csv` while preserving the other role definitions:

```csv
g, open-craft:Core, role:developer
```

For one-off debugging, edit the live ConfigMap carefully:

```bash
set -euo pipefail

kubectl edit configmap argocd-rbac-cm -n argocd
```

Example:

```yaml
# Please edit the object below. Lines beginning with a '#' will be ignored,
# and an empty file will abort the edit. If an error occurs while saving this file will be
# reopened with the relevant failures.
#
apiVersion: v1
data:
  policy.csv: |2-
    g, open-craft:Core, role:admin
    g, oc-sandboxuser, role:readonly
    g, sandboxuser, role:readonly
kind: ConfigMap
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: |
      {"apiVersion":"v1","kind":"ConfigMap","metadata":{"labels":{"app.kubernetes.io/name":"argocd-rbac-cm","app.kubernetes.io/part-of":"argocd"},"name":"argocd-rbac-cm","namespace":"argocd"}}
  creationTimestamp: "2026-01-19T17:20:36Z"
  labels:
    app.kubernetes.io/name: argocd-rbac-cm
    app.kubernetes.io/part-of: argocd
  name: argocd-rbac-cm
  namespace: argocd
  resourceVersion: "20663496"
  uid: 417d19a5-904f-4db6-9c7b-030ac839fbba
```

Once edited, make sure the argo-server is restarted `kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-server`.

## Verify SSO

Check the external ArgoCD URL:

```bash
set -euo pipefail

kubectl get configmap argocd-cm \
  -n argocd \
  -o jsonpath='{.data.url}{"\n"}'
```

It should be exactly `https://argocd.<cluster-domain>`.

Open `https://argocd.<cluster-domain>/`, select GitHub login, and complete the
OAuth flow. After login, the browser should remain authenticated and load the
ArgoCD applications UI.

If Dex and `argocd-server` report successful login but the browser returns to
the login page, check the ingress first:

```bash
set -euo pipefail

kubectl get ingress argocd-server-ingress \
  -n argocd \
  -o yaml
```

Make sure `nginx.ingress.kubernetes.io/app-root` is not present.

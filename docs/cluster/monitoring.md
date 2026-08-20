# Cluster Monitoring

This page describes monitoring options for the Launchpad cluster.

## Overview

When enabled via Harmony/Terraform, the stack can include:

- **Prometheus** -  Metrics collection from the cluster and applications
- **Grafana** -  Dashboards and visualization
- **Alertmanager** -  Alert routing and notifications

Configuration is typically done through Terraform variables (e.g. `prometheus_enabled`, `grafana_enabled`, `alertmanager_config`).

## Accessing Grafana

If Grafana is enabled, it is usually exposed at a hostname such as `grafana.<cluster-domain>`. Check the Terraform outputs or ingress resources:

```bash
kubectl get ingress -A | grep grafana
```

Use the credentials configured in Terraform or stored in a Kubernetes secret (e.g. in the same namespace as Grafana).

## Prometheus and Alertmanager

- **Prometheus** scrapes metrics from cluster and application targets. Queries can be run in Grafana or via the Prometheus UI if exposed.
- **Alertmanager** receives alerts from Prometheus and sends notifications (e.g. email, Slack). Configure receivers and routes in the Terraform/Alertmanager config.

## Open edX Instance Metrics

Instance-level monitoring (e.g. LMS, Celery, Redis) may be documented under [Instances -> Monitoring](../instances/monitoring.md). Ensure service monitors or scrape configs include the instance namespaces if you want them in cluster Prometheus.

## Related Documentation

- [Cluster Overview](index.md) -  Cluster operations
- [Infrastructure Overview](../infrastructure/index.md) -  Harmony and optional monitoring stack
- [Cluster Configuration](configuration.md) -  Terraform and monitoring variables
- [Instance Monitoring](../instances/monitoring.md) -  Instance-level monitoring

## See Also

- [Backup](backup.md) -  Backup and retention
- [Restore](restore.md) -  Restore procedures
- [User Guides Overview](../user-guides/index.md) -  Task-based guides

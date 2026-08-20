# Infrastructure Overview

The Launchpad stack provides a solution for hosting Open edX instances on Kubernetes. This overview describes the core components and how they work together to deliver a scalable, maintainable platform.

## Kubernetes

Kubernetes serves as the foundation of the infrastructure, providing container orchestration and cluster management capabilities. The platform leverages Kubernetes for:

- **Resource Management**: Automated scheduling, scaling, and management of containerized applications
- **Namespace Isolation**: Each Open edX instance runs in its own namespace, ensuring proper resource isolation and security boundaries
- **Configuration Management**: ConfigMaps and Secrets for application configuration and sensitive data
- **Persistent Storage**: Volume management for file storage (for services like Redis)

The infrastructure supports multiple cloud providers, including AWS (EKS) and DigitalOcean (DOKS), allowing organizations to choose the platform that best fits their requirements.

Other providers can be used if the external dependencies (mainly Harmony) are supporting them.

## ArgoCD

ArgoCD provides GitOps-based continuous delivery for the platform. It monitors the cluster repository and automatically synchronizes the desired state defined in the instance's manifests with the actual state in the Kubernetes cluster.

Key capabilities include:

- **Declarative Configuration**: Application definitions stored as code in the cluster repository per Open edX instance
- **Automated Synchronization**: Continuous monitoring and reconciliation of cluster state (if auto-sync is enabled)
- **Rollback Capabilities**: Easy reversion to previous application states

ArgoCD applications are created automatically for each Open edX instance, enabling declarative deployment and management of the entire platform stack. This allows selective auto-deployment for instances as desired.

## Argo Workflows

Argo Workflows orchestrates the [provisioning](./provisioning.md) and [deprovisioning](./deprovisioning.md) of users and infrastructure resources. It manages the lifecycle of databases, storage buckets, and other supporting services required by Open edX instances.

The workflow system handles:

- **Database Provisioning**: Automated creation of MySQL and MongoDB databases with proper credentials and access controls
- **Storage Setup**: Provisioning of S3-compatible storage buckets from tutor-contrib-s3 settings in the instance config (see [Object Storage](../instances/configuration.md#object-storage))
- **Resource Cleanup**: Automated deprovisioning workflows that safely remove resources when instances are deleted
- **Workflow Templates**: Reusable workflow definitions for consistent resource management across instances

## Harmony

Harmony is Open edX's project that provides Terraform modules and Kubernetes configurations for deploying Open edX on Kubernetes clusters. It includes:

- **Ingress Management**: Nginx-based ingress controllers with automatic TLS certificate management via Let's Encrypt
- **Monitoring Stack**: Optional Prometheus and Grafana integration for metrics collection and visualization
- **Backup Solutions**: Velero integration for cluster backup and disaster recovery
- **Resource Quotas**: Configurable resource limits and quotas for cluster components

The Harmony Terraform modules are integrated into the infrastructure provisioning process, ensuring consistent deployment of supporting services across different cloud providers.

## Tutor

Tutor is the official deployment tool for Open edX, providing a command-line interface for managing Open edX installations. In the Launchpad stack, Tutor is used to:

- **Generate Kubernetes Manifests**: Create Kubernetes YAML manifests to setup and configure services
- **Manage Open edX Versions**: Specify and build specific versions of the Open edX platform
- **Plugin Management**: Install and configure Tutor plugins that extend platform functionality
- **Configuration Management**: Centralized configuration through Tutor's environment-based settings

Each Open edX instance uses Tutor to generate its Kubernetes deployment manifests, which are then managed through ArgoCD deployments.

## Picasso

Picasso is a GitHub Actions-based workflow system for building Docker images for Open edX services. It automates the image build process and integrates with the deployment pipeline.

Picasso provides:

- **Automated Image Building**: GitHub Actions workflows that build Docker images for Open edX core services and Micro Frontends (MFEs)
- **Image Tag Management**: Automatic generation and updating of image tags in configuration files
- **Multi-Service Support**: Separate build workflows for different services (openedx, mfe, etc.)
- **Registry Integration**: Support for various container registries, including GitHub Container Registry (GHCR) that is used by this stack by default

The build workflows are **not triggered automatically** when changes are made to instance configurations. The build must be triggered manually (or by automation scripts) using GitHub Actions.

## Drydock

Drydock is a Tutor plugin that enhances Open edX deployments on Kubernetes. It provides additional functionality and optimizations specifically designed for ArgoCD based deployments.

Key features include:

- **Init Jobs**: Automated initialization tasks that run before the main application starts, such as database migrations and static asset collection
- **Kubernetes Optimizations**: Enhanced resource management and scheduling for Open edX workloads
- **Registry Credentials**: Secure handling of container registry authentication for private image pulls
- **Plugin Integration**: Seamless integration with other Tutor plugins in the Kubernetes deployment context

Drydock is automatically installed and enabled for all instances, ensuring that Open edX deployments benefit from Kubernetes-specific optimizations and best practices.

## Component Integration

These components work together to form a cohesive platform:

1. **Infrastructure Provisioning**: Terraform modules (including Harmony) provision the Kubernetes cluster and supporting infrastructure
2. **Image Building**: Picasso builds Docker images for Open edX services and updates configuration files
3. **Deployment**: ArgoCD monitors Git repositories and deploys applications using manifests generated by Tutor
4. **Resource Management**: Argo Workflows provisions databases and storage resources as needed
5. **Runtime**: Drydock enhances the Kubernetes deployment with optimized configurations and initialization tasks

This architecture provides a scalable, maintainable solution for hosting multiple Open edX instances with proper isolation, automated operations, and GitOps-based management. All based on maintained and open-source solutions.

## Related Documentation

- [Introduction](../index.md) -  Documentation home
- [Provisioning](provisioning.md) -  Cluster and ArgoCD provisioning steps
- [Cluster Repository Setup](cluster-repository-setup.md) -  GitHub secrets, workflows, and ArgoCD repository connection
- [Deprovisioning](deprovisioning.md) -  Removing infrastructure
- [Custom Resources](custom-resources.md) -  Workflow templates and ArgoCD resources

## See Also

- [Cluster Overview](../cluster/index.md) -  Cluster operations after provisioning
- [Instances Overview](../instances/index.md) -  Instance lifecycle
- [Instance Provisioning](../instances/provisioning.md) -  Creating Open edX instances

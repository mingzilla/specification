# Docker Deployment Specification

This document provides specifications for deploying the vector database system in AWS using Kubernetes.

## System Components

| Service                      | Container Image                       | Purpose                                                             | Ports                        |
|------------------------------|---------------------------------------|---------------------------------------------------------------------|------------------------------|
| **Ollama Embedding Service** | `mingzilla/ollama-nomic-embed:latest` | Provides text embedding generation using the nomic-embed-text model | 11434 (HTTP)                 |
| **Qdrant Vector Database**   | `qdrant/qdrant:latest`                | Stores and searches vector embeddings                               | 6333 (HTTP API), 6334 (gRPC) |

## Deployment Pattern

- Deploy **one set** of services (Ollama + Qdrant) **per customer cluster**
- Each Panintelligence dashboard cluster should have its own dedicated vector database services
- All nodes in a PI dashboard cluster share the same vector database services

## Network Configuration

### Security Model

- Primary security relies on **network isolation** via private subnet
- For any token verification requirements, use a **reverse proxy** in front of the services
- Both services should be deployed in a **private subnet**
- Access should be restricted to the PI dashboard application nodes only

### Connectivity Requirements

| Service               | Source          | Destination    | Port  | Protocol |
|-----------------------|-----------------|----------------|-------|----------|
| PI Dashboard → Ollama | Dashboard Nodes | Ollama Service | 11434 | HTTP     |
| PI Dashboard → Qdrant | Dashboard Nodes | Qdrant Service | 6333  | HTTP     |
| Ollama → Internet     | Ollama Service  | Internet       | 443   | HTTPS    |

## Resource Requirements

| Service | CPU                                        | Memory                             | Storage                           |
|---------|--------------------------------------------|------------------------------------|-----------------------------------|
| Ollama  | 2 cores (minimum)<br>4 cores (recommended) | 4GB (minimum)<br>8GB (recommended) | 2GB                               |
| Qdrant  | 1 core (minimum)<br>2 cores (recommended)  | 2GB (minimum)<br>4GB (recommended) | Ephemeral (see persistence notes) |

## Persistence Configuration

- **Qdrant**: No persistent volume needed
    - Vectors are rebuilt on service restart
    - This is an intentional design choice to avoid volume maintenance
    - The embedding model ensures consistent vector generation

- **Ollama**: No persistent volume needed
    - The custom image `mingzilla/ollama-nomic-embed` has the model pre-installed
    - No model downloading or storage is required

## Health Checks

| Service | Endpoint                             | Initial Delay | Interval | Timeout |
|---------|--------------------------------------|---------------|----------|---------|
| Ollama  | `http://localhost:11434/api/version` | 30s           | 10s      | 5s      |
| Qdrant  | `http://localhost:6333/health`       | 5s            | 10s      | 5s      |

## Scaling Considerations

- **Ollama**: Does not need to scale horizontally; vertical scaling recommended
- **Qdrant**: Does not need to scale horizontally for current workloads
- Resource allocation should be adjusted based on customer size and usage patterns

## Environment Variables and Configuration

### Environment Variables

| Service | Variable                     | Value     | Purpose                                         |
|---------|------------------------------|-----------|-------------------------------------------------|
| Ollama  | `OLLAMA_HOST`                | `0.0.0.0` | Binds to all network interfaces                 |
| Qdrant  | `QDRANT_ALLOW_RECOVERY_MODE` | `false`   | Prevents automatic recovery attempts on startup |

### Using a Reverse Proxy for Token Verification

If authentication is required for these services, we recommend implementing a reverse proxy:

1. **Deploy a reverse proxy** (such as NGINX or Envoy) in front of the Ollama and Qdrant services
2. **Configure the reverse proxy** to handle token verification
3. **Update the VectorStoreConfig** in your application to include the required tokens:

```java
VectorStoreConfig config = VectorStoreConfig.create(
        "http://ollama-service:11434/api/embeddings",  // Embedding service URL
        "nomic-embed-text",                            // Embedding model
        "your_ollama_token",                           // Token for Ollama (verified by reverse proxy)
        "http://qdrant-service:6333",                  // Qdrant URL
        "your_qdrant_token",                           // Token for Qdrant (verified by reverse proxy)
        "default",                                     // Namespace
        "vector_store"                                 // Collection name
);
```

The library will include these tokens in the appropriate headers when making requests to these services:

- For Ollama: Currently sent in a custom header, but will be changed to the Authorization header with Bearer format
- For Qdrant: Currently sent in the "api-key" header, but will be changed to the Authorization header with Bearer format

## Additional Notes

1. **Service Discovery**:
    - Use standard Kubernetes service discovery
    - Services should be accessible within the cluster by name

2. **Monitoring**:
    - Both services expose metrics that can be scraped by Prometheus
    - Qdrant exposes metrics at `/metrics`

3. **Disaster Recovery**:
    - No special backup procedures required
    - The system is designed to rebuild vectors as needed

4. **Deployment Schedule**:
    - Services can be deployed ahead of PI dashboard updates
    - No special initialization is required beyond container startup

5. **Rolling Updates**:
    - Standard Kubernetes rolling update procedures can be used
    - No special handling required for upgrades

6. **Security Considerations**:
    - The primary security mechanism should be network isolation via VPC/private subnet
    - If token verification is needed, implement it consistently via a reverse proxy
    - Store authentication tokens in Kubernetes secrets or other secure credential storage
    - Rotate tokens periodically according to your security policy
    - Token verification provides an additional layer of protection if network configuration errors occur
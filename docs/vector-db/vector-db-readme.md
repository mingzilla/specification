# Vector Database Library

A high-performance, reactive Java library for semantic search using vector embeddings with Qdrant and Ollama.

## Features

- **Semantic Search**: Find similar content based on meaning rather than keywords
- **Reactive API**: Built on Project Reactor for non-blocking operations
- **Distributed Locking**: Coordinated operations across multiple application nodes
- **Auto-loading**: Smart collection initialization with just-in-time loading
- **Attribute Filtering**: Filter search results using advanced attribute matching
- **Namespace Support**: Organize collections in logical groups
- **Comprehensive Events**: Track operation lifecycles through event streams
- **Diagnostics Integration**: Built-in troubleshooting capabilities

## Quick Start

```java
public void usage() {
    // Create service with configuration
    VectorDbService vectorDbService = new VectorDbService();

    // Use config with authentication tokens if services require them
    VectorStoreConfig config = VectorStoreConfig.create(
            "http://localhost:11434/api/embeddings",  // Embedding service URL
            "nomic-embed-text",                       // Embedding model
            "embedding_token",                        // Token for Ollama (if required by reverse proxy)
            "http://localhost:6333",                  // Qdrant URL
            "qdrant_token",                           // Token for Qdrant (if required by reverse proxy)
            "default",                                // Namespace
            "vector_store"                            // Collection name
    );

    // Add a record with attributes
    VectorDbInput record = new VectorDbInput(
            1,                                              // ID
            "Sales by Region",                              // Name
            List.of(                                        // Attributes
                    new AttributeGroup("dimensions", List.of("Region", "Date")),
                    new AttributeGroup("measures", List.of("Sales Amount", "Quantity"))
            ),
            System.currentTimeMillis()                      // Updated timestamp
    );

    // Store the record with auto-initialization if needed
    vectorDbService.upsertOrLoadRecords(
            config,
            record,
            () -> Mono.just(List.of(record)) // Supply all records if collection is empty
    ).block();

    // Search for similar records
    String query = "sales performance by geographical area";
    int limit = 5;
    VectorDbQuery searchQuery = VectorDbQuery.basic(query, limit);

    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, searchQuery)
            .block();

    // Process results
    results.forEach(result -> {
        System.out.println("ID: " + result.id() + ", Score: " + result.score());
        System.out.println("Name: " + result.name());
    });
}
```

## Requirements

- Java 17 or later
- Qdrant vector database (available via Docker)
- Ollama embedding service with `nomic-embed-text` model

## Setup with Docker Compose

For local development, you can run the required services using Docker Compose:

```yaml
services:
  ollama:
    image: mingzilla/ollama-nomic-embed:latest
    container_name: ollama-service
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant-service
    ports:
      - "6333:6333"    # REST API
      - "6334:6334"    # gRPC API
    environment:
      - QDRANT_ALLOW_RECOVERY_MODE=false
    restart: unless-stopped
```

Start the services:

```bash
docker-compose up -d
```

The services will be available at:

- Ollama: http://localhost:11434
- Qdrant: http://localhost:6333

Note: Both services can be placed behind a reverse proxy for token verification if needed in secure environments. The library supports sending authentication tokens through `VectorStoreConfig` for both services when required.

### Deployment Notes

- **Local Development**: The Docker Compose setup above is primarily for local development and testing.
- **Production Deployment**: For production, refer to the [Docker Deployment Specification](docker-deployment-spec.md) for proper configuration in cloud environments.
- **Security Model**: The primary security mechanism should rely on network isolation (VPC). If token verification is needed, implement it in a reverse proxy rather than directly in the services.
- **No-Volume Design**: We intentionally run Qdrant without persistent volumes to allow fresh rebuilding of vectors when starting the service, eliminating the need for volume maintenance.
- **Pre-built Embedding Image**: The `mingzilla/ollama-nomic-embed` image comes with the embedding model pre-installed, eliminating the need for model downloading and maintenance.

## Documentation

- [API Manual](vector-db-api-manual.md): Comprehensive documentation with examples
- [Behavior Specification](vector-db-behaviour-spec.md): Technical details and behavior scenarios

## Key Components

The library consists of these main components:

- **VectorDbService**: Primary entry point for all operations
- **VectorStoreConfig**: Configuration for embedding and storage services
- **VectorDbInput/Record**: Data models for vectors and their attributes
- **VectorDbQuery**: Search query model with filtering capabilities
- **AttributeFilter**: Filtering mechanism for search refinement

## Related Documents

- [**Vector Database Library API Manual**](vector-db-api-manual.md): Comprehensive API documentation with examples
- [**Vector Database Library Behavior Specification**](vector-db-behaviour-spec.md): Technical details and behavior scenarios
- [**Docker Deployment Specification**](vector-db-docker-deployment.md): Detailed deployment guide for cloud environments
- [**Docker Deployment Options**](vector-db-deployment-options-analysis.md): Analysis of different deployment options

## License

[MIT License](LICENSE)
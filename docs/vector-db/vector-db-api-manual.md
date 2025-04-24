# Vector Database Library Manual

This manual provides a comprehensive guide for using the Vector Database library, which enables semantic search capabilities through vector embeddings stored in Qdrant.

## Table of Contents

- [Vector Database Library Manual](#vector-database-library-manual)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Key Components](#key-components)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
  - [Basic Operations](#basic-operations)
    - [Creating and Configuring the Service](#creating-and-configuring-the-service)
    - [Adding Records](#adding-records)
    - [Searching Records](#searching-records)
    - [Updating Records](#updating-records)
    - [Removing Records](#removing-records)
    - [Rebuilding the Index](#rebuilding-the-index)
    - [Collection Management](#collection-management)
  - [Working with Namespaces](#working-with-namespaces)
    - [Listing Namespaces](#listing-namespaces)
    - [Listing Collections by Namespace](#listing-collections-by-namespace)
    - [Deleting a Namespace](#deleting-a-namespace)
  - [Advanced Search with Filtering](#advanced-search-with-filtering)
    - [Basic Search](#basic-search)
    - [Search with Score Threshold](#search-with-score-threshold)
    - [Filtering with Match Any Strategy](#filtering-with-match-any-strategy)
    - [Filtering with Match All Strategy](#filtering-with-match-all-strategy)
    - [Combined Filtering](#combined-filtering)
  - [Event Tracking](#event-tracking)
  - [Distributed Locking](#distributed-locking)
  - [Best Practices](#best-practices)
  - [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Enabling Diagnostics](#enabling-diagnostics)

## Overview

This library provides a high-level interface for working with vector embeddings stored in a Qdrant vector database. Key features include:

- Semantic search based on vector similarity
- Attribute-based filtering
- Support for namespaces to organize collections
- Batch processing for efficient data loading
- Distributed locks for concurrent operations
- Event tracking for operation monitoring

The library automatically handles the integration with embedding services (Ollama) to generate vector embeddings from text, and manages the storage and retrieval of these embeddings in Qdrant.

## Key Components

The primary classes you'll need to use are:

- **VectorDbService**: The main entry point for all operations
- **VectorStoreConfig**: Configuration parameters for both embedding generation and vector storage
- **VectorDbInput**: Input data model for creating/updating records
- **VectorDbQuery**: Query model for searching with filtering capabilities
- **AttributeFilter**: Utility for creating search filters with different matching strategies
- **VectorDbEvent**: Event model for tracking operation progress

## Getting Started

### Prerequisites

- Qdrant running at http://localhost:6333
- Ollama embedding service running at http://localhost:11434
- The "nomic-embed-text" model loaded in Ollama

## Basic Operations

### Creating and Configuring the Service

```java
import com.panintelligence.vector.VectorDbService;
import com.panintelligence.vector.model.VectorStoreConfig;

// Create service
VectorDbService vectorDbService = new VectorDbService();

// Create configuration with authentication tokens (if required by reverse proxy)
VectorStoreConfig config = VectorStoreConfig.create(
        "http://embedding-service:11434/api/embeddings", // Embedding service URL
        "nomic-embed-text",                              // Embedding model
        "embedding_token",                               // Token for Ollama authentication (if required)
        "http://qdrant-service:6333",                    // Qdrant URL
        "qdrant_token",                                  // Token for Qdrant authentication (if required)
        "my-namespace",                                  // Collection namespace
        "my-collection"                                  // Collection name
);
```

Note: Authentication tokens for both Ollama and Qdrant are optional and should be provided only if the services are configured to require token verification (typically via a reverse proxy). The library will include the tokens in the appropriate headers when making requests to these services.

### Adding Records

```java
import com.panintelligence.vector.model.AttributeGroup;
import com.panintelligence.vector.model.VectorDbInput;
import reactor.core.publisher.Mono;

import java.util.List;

// Create an input record
VectorDbInput record = new VectorDbInput(
    1,                                              // Unique record ID
    "Sales by Region",                              // Record name
    List.of(                                        // Attribute groups
        new AttributeGroup("dimensions", List.of("Region", "Date")),
        new AttributeGroup("measures", List.of("Sales Amount", "Quantity"))
    ),
    System.currentTimeMillis()                      // Updated timestamp
);

// Smart upsert with auto-loading (recommended approach)
vectorDbService.upsertOrLoadRecords(
    config, 
    record, 
    () -> Mono.just(allRecords) // Supplier for all records if collection is empty
).block();

// Add multiple records in batch
List<VectorDbInput> records = List.of(record1, record2, record3);
vectorDbService.loadRecords(config, records).block();

// Initialize collection if empty
vectorDbService.loadRecordsIfEmpty(config, records).block();
```

### Searching Records

```java
import com.panintelligence.vector.model.VectorDbQuery;
import com.panintelligence.vector.model.VectorDbSearchResult;

// Basic search query
String query = "sales performance by geographical area";
int limit = 5;
VectorDbQuery basicQuery = VectorDbQuery.basic(query, limit);

// Execute search
List<VectorDbSearchResult> results = vectorDbService
    .findRelevantRecords(config, basicQuery)
    .block();

// Process results
for (VectorDbSearchResult result : results) {
    System.out.println("ID: " + result.id());
    System.out.println("Name: " + result.name());
    System.out.println("Score: " + result.score());
    System.out.println("Attributes: " + result.attributeGroups());
    System.out.println("---");
}
```

### Updating Records

```java
// Upsert a record (update if exists, insert if not)
VectorDbInput updatedRecord = new VectorDbInput(
    1,                                              // Existing ID to update
    "Sales by Region (Updated)",                    // Updated name
    List.of(new AttributeGroup("dimensions", List.of("Region", "Date", "Product"))),
    System.currentTimeMillis()                      // Current timestamp
);

// Smart upsert with auto-detection of collection state
vectorDbService.upsertOrLoadRecords(
    config, 
    updatedRecord, 
    () -> Mono.just(allRecords) // Supplier for all records if collection is empty
).block();
```

### Removing Records

```java
// Remove a record by ID
Integer recordIdToRemove = 1;
vectorDbService.removeRecord(config, recordIdToRemove).block();

// Remove multiple records
List<Integer> recordIds = List.of(1, 2, 3);
vectorDbService.removeRecords(config, recordIds).block();
```

### Rebuilding the Index

```java
// Get all records (e.g., from your database)
List<VectorDbInput> allRecords = getAllRecordsFromDatabase();

// Rebuild the entire index (removes all existing records and adds new ones)
int batchSize = 10;
vectorDbService.rebuildIndex(config, allRecords, batchSize).block();
```

### Collection Management

```java
// Check if a collection exists
Boolean exists = vectorDbService.collectionExists(config).block();

// Delete a collection
vectorDbService.deleteCollection(config).block();

// Clear all records in a collection but keep the collection structure
vectorDbService.clearCollection(config).block();
```

## Working with Namespaces

Namespaces provide a way to organize collections, similar to schemas in a relational database.

### Listing Namespaces

```java
// List all namespaces
Set<String> namespaces = vectorDbService.listNamespaces(config).block();
System.out.println("Available namespaces: " + namespaces);
```

### Listing Collections by Namespace

```java
// List collections in a specific namespace
String namespace = "my-namespace";
List<String> collections = vectorDbService
    .listCollectionsByNamespace(config, namespace)
    .block();

System.out.println("Collections in namespace '" + namespace + "': " + collections);
```

### Deleting a Namespace

```java
// Delete all collections in a namespace
String namespaceToDelete = "old-namespace";
boolean confirmDelete = true; // Safety flag to prevent accidental deletion

Integer deletedCount = vectorDbService
    .deleteNamespace(config, namespaceToDelete, confirmDelete)
    .block();

System.out.println("Deleted " + deletedCount + " collections from namespace '" + namespaceToDelete + "'");
```

## Advanced Search with Filtering

### Basic Search

```java
// Simple search with just a query and limit
VectorDbQuery query = VectorDbQuery.basic("customer satisfaction", 5);
```

### Search with Score Threshold

```java
// Search with a minimum score threshold
VectorDbQuery query = new VectorDbQuery.Builder()
    .limit(10)
    .scoreThreshold(0.75f) // Only return results with similarity >= 0.75
    .build("customer satisfaction");
```

### Filtering with Match Any Strategy

```java
import com.panintelligence.vector.model.AttributeFilter;

// Find records that have EITHER "Region" OR "Product" as dimensions
VectorDbQuery query = new VectorDbQuery.Builder()
    .limit(10)
    .withFilter(
        AttributeFilter.matchAny("dimensions", List.of("Region", "Product"))
    )
    .build("sales analysis");
```

### Filtering with Match All Strategy

```java
// Find records that have BOTH "Region" AND "Date" as dimensions
VectorDbQuery query = new VectorDbQuery.Builder()
    .limit(10)
    .withFilter(
        AttributeFilter.matchAll("dimensions", List.of("Region", "Date"))
    )
    .build("sales trends over time by region");
```

### Combined Filtering

```java
// Complex query with multiple filters
// Find records that:
// 1. Have EITHER "Region" OR "Store" as dimensions (matchAny)
// 2. AND have "Sales Amount" as a measure (matchAll)
VectorDbQuery query = new VectorDbQuery.Builder()
    .limit(10)
    .scoreThreshold(0.6f)
    .withFilter(
        AttributeFilter.matchAny("dimensions", List.of("Region", "Store"))
    )
    .withFilter(
        AttributeFilter.matchAll("measures", List.of("Sales Amount"))
    )
    .build("regional sales performance");
```

## Event Tracking

The VectorDbService emits events for all major operations that can be subscribed to for monitoring:

```java
// Subscribe to events from the service
vectorDbService.eventSubject.asFlux()
    .subscribe(event -> {
        System.out.println("Event: " + event.type());
        System.out.println("Config: " + event.config().vectorDbParams().getCollectionFullName());
        System.out.println("Data: " + event.data());
    });
```

Available event types include:

```java
// Load Records events
LOAD_RECORDS__START
LOAD_RECORDS__LOAD_IN_PROGRESS
LOAD_RECORDS__LOCK_ACQUIRED
LOAD_RECORDS__LOCK_FAILED_TO_ACQUIRE
LOAD_RECORDS__START_EMBEDDING
LOAD_RECORDS__SUCCEEDED
LOAD_RECORDS__FAILED
LOAD_RECORDS__ENDED

// Upsert Auto-Load events
UPSERT_OR_LOAD__START
UPSERT_OR_LOAD__DISTRIBUTED_LOCK_DETECTED
UPSERT_OR_LOAD__LOCAL_LOAD_IN_PROGRESS
UPSERT_OR_LOAD__BATCH__SUBSCRIBED
UPSERT_OR_LOAD__BATCH__SUCCEEDED
UPSERT_OR_LOAD__BATCH__FAILED
UPSERT_OR_LOAD__BATCH__ENDED
UPSERT_OR_LOAD__SINGLE__SUBSCRIBED
UPSERT_OR_LOAD__SINGLE__SUCCEEDED
UPSERT_OR_LOAD__SINGLE__FAILED
UPSERT_OR_LOAD__SINGLE__ENDED
```

You can create an event handler to log or process these events:

```java
private void processEvent(VectorDbEvent event) {
    switch (event.type()) {
        case LOAD_RECORDS__SUCCEEDED:
            logger.info("Successfully loaded all records");
            break;
        case UPSERT_OR_LOAD__BATCH__SUBSCRIBED:
            logger.info("Auto-loading collection because it was empty");
            break;
        case LOAD_RECORDS__FAILED:
            logger.error("Failed to load records: {}", event.data());
            break;
        // Handle other events as needed
    }
}
```

## Distributed Locking

The library uses a distributed locking mechanism to coordinate operations between multiple application instances:

```java
// Check if lock service is available
Boolean lockServiceAvailable = vectorDbService.isLockServiceAvailable(config).block();
```

The locking mechanism is automatically used by various operations:

1. `loadRecords` - Acquires a distributed lock named "batch_processing" for the collection
2. `rebuildIndex` - Acquires a distributed lock named "rebuild_index" for the collection
3. `deleteNamespace` - Acquires a distributed lock named "delete_namespace" for the namespace
4. `upsertOrLoadRecords` - Checks for existing distributed locks before proceeding

Implementation details:

- Locks are stored as vector records in a dedicated "vector_locks" collection in Qdrant
- Each lock contains node identity information to track which node holds the lock
- Locks automatically expire after 5 minutes to prevent deadlocks if a node crashes
- The system can detect locks held by other nodes and will adjust behavior accordingly

## Best Practices

1. **Unique IDs**: Ensure record IDs are unique within a collection to avoid unintended updates.

2. **Use Smart Upsert**: Prefer `upsertOrLoadRecords` for automatic handling of empty collections:
   ```java
   vectorDbService.upsertOrLoadRecords(config, record, () -> Mono.just(allRecords)).block();
   ```

3. **Batch Processing**: Use batch loading for multiple records to improve performance:
   ```java
   vectorDbService.loadRecords(config, records).block();
   ```

4. **Namespaces**: Use namespaces to organize collections by domain or application.

5. **Attribute Structure**: Organize attributes in logical groups for better filtering:
   ```java
   List<AttributeGroup> attributes = List.of(
       new AttributeGroup("dimensions", List.of("Region", "Date")),
       new AttributeGroup("measures", List.of("Sales", "Profit")),
       new AttributeGroup("tags", List.of("dashboard", "executive"))
   );
   ```

6. **Descriptive Names**: Use descriptive record names to improve semantic search:
   ```java
   VectorDbInput record = new VectorDbInput(
       1,
       "Monthly Sales Performance by Region and Product Category",
       attributes,
       timestamp
   );
   ```

7. **Event Monitoring**: Subscribe to events for visibility into operations:
   ```java
   vectorDbService.eventSubject.asFlux().subscribe(this::processEvent);
   ```

8. **Connection Management**: Close the service when done:
   ```java
   vectorDbService.close();
   ```

9. **Security Model**: 
   - Primary security should rely on network isolation (VPC)
   - If token verification is needed, implement it in a reverse proxy rather than directly in the services
   - Supply authentication tokens in the `VectorStoreConfig` when required by the reverse proxy
   - The library supports sending these tokens with requests to both services

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Ensure Qdrant is running at the configured URL
   - Check if Ollama embedding service is running

2. **Authentication Failures**:
   - Verify authentication tokens are correct in the VectorStoreConfig if your services require token verification
   - Check if the reverse proxy is properly configured to validate tokens
   - Make sure the token format matches what the reverse proxy expects

3. **Invalid Embedding Vectors**:
   - Verify the embedding model is correctly loaded in Ollama

4. **Collection Not Found**:
   - Check that the namespace and collection name are correctly configured
   - Verify the collection exists using listCollectionsByNamespace

5. **Performance Issues**:
   - Use appropriate batch sizes for your data volume
   - Consider increasing connection pool sizes for high concurrency

6. **Lock Acquisition Failures**:
   - Ensure Qdrant service is accessible 
   - Check if another process is holding the lock
   - Monitor for events indicating lock failures

### Enabling Diagnostics

The library integrates with a diagnostics framework for visibility into operations:

```java
// Enable vector database diagnostics
VectorDbDiagnostics.enable();

// Get diagnostic summary
String summary = VectorDbDiagnostics.getSummary();

// Disable diagnostics
VectorDbDiagnostics.disable();
```
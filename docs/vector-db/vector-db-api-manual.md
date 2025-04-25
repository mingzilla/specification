# Vector Database Library Documentation

This document provides comprehensive documentation for using the Vector Database library, which enables semantic search capabilities through vector embeddings stored in Qdrant.

## Table of Contents

- [Overview](#overview)
- [Key Components](#key-components)
- [Prerequisites](#prerequisites)
- [Code Examples](#code-examples)
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
    - [Diagnostics](#diagnostics)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)

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

## Prerequisites

- Qdrant running at http://localhost:6333
- Ollama embedding service running at http://localhost:11434
- The "nomic-embed-text" model loaded in Ollama

## Code Examples

The examples below demonstrate how to use the Vector Database library for various operations. Each example can be found as a method in the `BasicOperations` class (see [Complete Example Class](#complete-example-class)).

### Creating and Configuring the Service

To get started, create and configure the VectorDbService:

```java
public VectorStoreConfig createAndConfigureService() {
    return VectorStoreConfig.create(
            "http://embedding-service:11434/api/embeddings", // Embedding service URL
            "nomic-embed-text",                              // Embedding model
            "embedding_token",                               // Token for Ollama authentication (if required)
            "http://qdrant-service:6333",                    // Qdrant URL
            "qdrant_token",                                  // Token for Qdrant authentication (if required)
            "my-namespace",                                  // Collection namespace
            "my-collection"                                  // Collection name
    );
}
```

Note: Authentication tokens for both Ollama and Qdrant are optional and should be provided only if the services are configured to require token verification (typically via a reverse proxy).

### Adding Records

There are several ways to add records to the vector database:

```java
public void addingRecords() {
    VectorStoreConfig config = createAndConfigureService();

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

    // Create a list of all records (for collection initialization)
    List<VectorDbInput> allRecords = List.of(record);

    // Smart upsert with auto-loading (recommended approach)
    vectorDbService.upsertOrLoadRecords(
            config,
            record,
            () -> Mono.just(allRecords) // Supplier for all records if collection is empty
    ).block();

    // Add multiple records in batch
    List<VectorDbInput> records = List.of(record1, record2, record3);
    vectorDbService.loadRecords(config, () -> Mono.just(records)).block();

    // Initialize collection if empty
    vectorDbService.loadRecordsIfEmpty(config, records).block();
}
```

### Searching Records

Perform basic searches with the vector database:

```java
public void searchingRecords() {
    VectorStoreConfig config = createAndConfigureService();

    // Basic search query
    String query = "sales performance by geographical area";
    int limit = 5;
    VectorDbQuery basicQuery = VectorDbQuery.basic(query, limit);

    // Execute search
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, basicQuery)
            .block();

    // Process results
    if (results != null) {
        for (VectorDbSearchResult result : results) {
            System.out.println("ID: " + result.id());
            System.out.println("Name: " + result.name());
            System.out.println("Score: " + result.score());
            System.out.println("Attributes: " + result.attributeGroups());
            System.out.println("---");
        }
    }
}
```

### Updating Records

Update existing records using the smart upsert method:

```java
public void updatingRecords() {
    VectorStoreConfig config = createAndConfigureService();

    // Create a list of all records (for collection initialization)
    List<VectorDbInput> allRecords = getAllRecordsFromDatabase();

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
}
```

### Removing Records

Remove records individually or in batch:

```java
public void removingRecords() {
    VectorStoreConfig config = createAndConfigureService();

    // Remove a record by ID
    Integer recordIdToRemove = 1;
    vectorDbService.removeRecord(config, recordIdToRemove).block();

    // Remove multiple records
    List<Integer> recordIds = List.of(1, 2, 3);
    vectorDbService.removeRecords(config, recordIds).block();
}
```

### Rebuilding the Index

Completely rebuild a collection index:

```java
public void rebuildingTheIndex() {
    VectorStoreConfig config = createAndConfigureService();

    // Get all records (e.g., from your database)
    List<VectorDbInput> allRecords = getAllRecordsFromDatabase();

    // Rebuild the entire index (removes all existing records and adds new ones)
    vectorDbService.rebuildIndex(config, allRecords).block();
}
```

### Collection Management

Manage vector database collections:

```java
public void collectionManagement() {
    VectorStoreConfig config = createAndConfigureService();

    // Check if a collection exists
    Boolean exists = vectorDbService.collectionExists(config).block();

    // Delete a collection
    vectorDbService.deleteCollection(config).block();

    // Clear all records in a collection but keep the collection structure
    vectorDbService.clearCollection(config).block();
}
```

### Working with Namespaces

Namespaces provide a way to organize collections, similar to schemas in a relational database.

#### Listing Namespaces

List all available namespaces:

```java
public void listingNamespaces() {
    VectorStoreConfig config = createAndConfigureService();

    // List all namespaces
    Set<String> namespaces = vectorDbService.listNamespaces(config).block();
    System.out.println("Available namespaces: " + namespaces);
}
```

#### Listing Collections by Namespace

List collections within a specific namespace:

```java
public void listingCollectionsByNamespace() {
    VectorStoreConfig config = createAndConfigureService();

    // List collections in a specific namespace
    String namespace = "my-namespace";
    List<String> collections = vectorDbService
            .listCollectionsByNamespace(config, namespace)
            .block();

    System.out.println("Collections in namespace '" + namespace + "': " + collections);
}
```

#### Deleting a Namespace

Delete all collections within a namespace:

```java
public void deletingANamespace() {
    VectorStoreConfig config = createAndConfigureService();

    // Delete all collections in a namespace
    String namespaceToDelete = "old-namespace";
    boolean confirmDelete = true; // Safety flag to prevent accidental deletion

    Integer deletedCount = vectorDbService
            .deleteNamespace(config, namespaceToDelete, confirmDelete)
            .block();

    System.out.println("Deleted " + deletedCount + " collections from namespace '" + namespaceToDelete + "'");
}
```

### Advanced Search with Filtering

The library provides advanced search capabilities with various filtering options.

#### Basic Search

Simple search with just a query and limit:

```java
public void basicSearch() {
    // Simple search with just a query and limit
    VectorDbQuery query = VectorDbQuery.basic("customer satisfaction", 5);

    VectorStoreConfig config = createAndConfigureService();
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, query)
            .block();
}
```

#### Search with Score Threshold

Search with a minimum score threshold:

```java
public void searchWithScoreThreshold() {
    // Search with a minimum score threshold
    VectorDbQuery query = new VectorDbQuery.Builder()
            .limit(10)
            .scoreThreshold(0.75f) // Only return results with similarity >= 0.75
            .build("customer satisfaction");

    VectorStoreConfig config = createAndConfigureService();
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, query)
            .block();
}
```

#### Filtering with Match Any Strategy

Find records that match ANY of the specified attributes:

```java
public void filteringWithMatchAnyStrategy() {
    // Find records that have EITHER "Region" OR "Product" as dimensions
    VectorDbQuery query = new VectorDbQuery.Builder()
            .limit(10)
            .withFilter(
                    AttributeFilter.matchAny("dimensions", List.of("Region", "Product"))
            )
            .build("sales analysis");

    VectorStoreConfig config = createAndConfigureService();
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, query)
            .block();
}
```

#### Filtering with Match All Strategy

Find records that match ALL of the specified attributes:

```java
public void filteringWithMatchAllStrategy() {
    // Find records that have BOTH "Region" AND "Date" as dimensions
    VectorDbQuery query = new VectorDbQuery.Builder()
            .limit(10)
            .withFilter(
                    AttributeFilter.matchAll("dimensions", List.of("Region", "Date"))
            )
            .build("sales trends over time by region");

    VectorStoreConfig config = createAndConfigureService();
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, query)
            .block();
}
```

#### Combined Filtering

Use multiple filters together:

```java
public void combinedFiltering() {
    // Complex query with multiple filters
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

    VectorStoreConfig config = createAndConfigureService();
    List<VectorDbSearchResult> results = vectorDbService
            .findRelevantRecords(config, query)
            .block();
}
```

### Event Tracking

Monitor vector database operations through events:

```java
public void eventTracking() {
    // Subscribe to events from the service
    vectorDbService.eventSubject.asFlux()
            .subscribe(event -> {
                System.out.println("Event: " + event.type());
                System.out.println("Config: " + event.config().vectorDbParams().getCollectionFullName());
                System.out.println("Data: " + event.data());
            });

    // Process specific event types
    private void processEvent (VectorDbEvent event){
        if (event == null) return;

        switch (event.type()) {
            case LOAD_RECORDS__SUCCEEDED:
                System.out.println("Successfully loaded all records");
                break;
            case UPSERT_OR_LOAD__BATCH__SUBSCRIBED:
                System.out.println("Auto-loading collection because it was empty");
                break;
            case LOAD_RECORDS__FAILED:
                System.out.println("Failed to load records: " + event.data());
                break;
            // Handle other events as needed
            default:
                System.out.println("Other event received: " + event.type());
                break;
        }
    }
}
```

### Distributed Locking

Check for distributed lock service availability:

```java
public void distributedLocking() {
    VectorStoreConfig config = createAndConfigureService();

    // Check if lock service is available
    Boolean lockServiceAvailable = vectorDbService.isLockServiceAvailable(config).block();
    System.out.println("Lock service available: " + lockServiceAvailable);
}
```

The locking mechanism is automatically used by various operations:

1. `loadRecords` - Acquires a distributed lock named "batch_processing" for the collection
2. `rebuildIndex` - Acquires a distributed lock named "rebuild_index" for the collection
3. `deleteNamespace` - Acquires a distributed lock named "delete_namespace" for the namespace
4. `upsertOrLoadRecords` - Checks for existing distributed locks before proceeding

## Best Practices

1. **Unique IDs**: Ensure record IDs are unique within a collection to avoid unintended updates.

2. **Use Smart Upsert**: Prefer `upsertOrLoadRecords` for automatic handling of empty collections:
   ```java
   vectorDbService.upsertOrLoadRecords(config, record, () -> Mono.just(allRecords)).block();
   ```

3. **Batch Processing**: Use batch loading for multiple records to improve performance:
   ```java
   vectorDbService.loadRecords(config, () -> Mono.just(records)).block();
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

### Diagnostics

Enable and use diagnostics for troubleshooting:

```java
public void enablingDiagnostics() {
    // Enable vector database diagnostics
    VectorDbDiagnostics.enable();

    // Get diagnostic summary
    String summary = VectorDbDiagnostics.getSummary();
    System.out.println("Diagnostics summary: " + summary);

    // Disable diagnostics
    VectorDbDiagnostics.disable();
}
```
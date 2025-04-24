# Vector Database System Specification

## Problem Statement

In vector database operations, we require the collection to be complete with all records loaded before performing individual upsert operations. Without completeness guarantees:
- Queries against partial collections yield inaccurate results
- Embedding models lose context from missing records
- System behavior becomes unpredictable

## Dual-Layer Locking Mechanism

| Lock Type | Implementation | Scope | Primary Purpose | Advantage |
|-----------|----------------|-------|----------------|-----------|
| **Local Lock** | In-memory atomic flag (`loadInProgress`) | Single application node | Prevents redundant operations on the same node | Low overhead, no network communication required |
| **Distributed Lock** | Managed by `VectorDbLockManager` using Qdrant | Across all application nodes | Coordinates operations between multiple application instances | Ensures only one node performs global operations, prevents duplicate initialization |

## Upsert with AutoLoad Operation Flows

### Path 1: Empty Collection Detection
```
Local Lock Check → Record Count Check → Distributed Lock Acquisition → Load All Records → Release Locks
   (atomic flag)      (count = 0)        (via VectorDbLockManager)     (batch load)      (both locks)
```

### Path 2: Existing Collection Upsert
```
Local Lock Check → Record Count Check → Single Record Upsert
   (not active)      (count > 0)       (individual operation)
```

### Path 3: Lock Detection (Efficiency)
```
Distributed Lock Check ────┐
  (lock detected)          ↓
         Set Temporary Local Lock (10s timeout) → Skip Operation
                        OR
Local Lock Check ──────────┐
 (already active)          ↓
                   Skip Operation
```

The implementation intelligently handles these flows to ensure collection completeness, prevent concurrent conflicts, and optimize system resources.

## Key Vector Database Operations

| Operation | When Used | Lock Requirements | Behavior |
|-----------|-----------|------------------|----------|
| **Loading All Items** (`loadRecords`) | • Collection is empty (count = 0)<br>• System initialization<br>• Full rebuild requested | Both local and distributed locks required | • Blocks other operations<br>• Loads records sequentially with controlled concurrency<br>• Uses `concatMap` for guaranteed sequential processing |
| **Upserting with Auto-Load** (`upsertOrLoadRecords`) | • Smart operation that checks collection state<br>• Handles both empty and populated collections | Conditional locking based on collection state | • Checks for distributed locks first<br>• If collection empty, loads all records<br>• If collection has data, performs single upsert |
| **Upserting One Item** (internal `upsertRecord`) | • Collection exists and has data<br>• Single record update required | No locks required | • Fast, targeted update<br>• Only affects specific vector record<br>• Minimizes system impact |
| **Deleting Items** (`removeRecord`, `removeRecords`) | • Individual record removal<br>• Batch record removal | No locks required | • Targeted deletion of specific records<br>• Does not affect other records<br>• Performs basic collection existence check |
| **Collection Operations** (`clearCollection`, `deleteCollection`) | • Collection rebuild requested<br>• Data purge operations | No locks required | • `clearCollection`: Removes all records but keeps collection structure<br>• `deleteCollection`: Completely removes the collection |
| **Namespace Operations** (`deleteNamespace`) | • Namespace cleanup required<br>• Multiple collection management | Distributed lock required | • Removes all collections within a namespace<br>• Requires explicit confirmation flag for safety<br>• Uses collection listing to find target collections |

## Lock Behavior in Different Scenarios

- **Local Lock Only**: Prevents concurrent operations on the same node but doesn't prevent operations from other nodes
  - Implemented using `AtomicBoolean loadInProgress` for fast local checking
  - Used for preventing duplicate load attempts from the same node

- **Distributed Lock Only**: Prevents operations across all nodes but has higher overhead for each check
  - Implemented through `VectorDbLockManager` using vectors in Qdrant
  - Contains node identifier, acquisition time, and expiration time
  - Used for coordinating namespace operations across nodes

- **Both Locks Together**: Provides complete protection with optimized performance
  - Local check happens first (efficient): `if (!loadInProgress.compareAndSet(false, true))`
  - Distributed check follows: `lockManager.acquireLock(vectorStoreConfig, collectionName, "batch_processing")`
  - Special handling for distributed lock detection: when a distributed lock is detected, a temporary local lock is set with 10-second timeout using `TimedExecutor.enableWithDuration(loadInProgress::set, 10)`
  - Every distributed lock operation has proper timeout and error handling

## Event Tracking System

The Vector Database Service includes a comprehensive event tracking system using `VectorDbEvent` to monitor operations:

| Event Category | Events | Purpose |
|----------------|--------|---------|
| **Load Records** | `LOAD_RECORDS__START`, `LOAD_RECORDS__LOAD_IN_PROGRESS`, `LOAD_RECORDS__LOCK_ACQUIRED`, `LOAD_RECORDS__LOCK_FAILED_TO_ACQUIRE`, `LOAD_RECORDS__START_EMBEDDING`, `LOAD_RECORDS__SUCCEEDED`, `LOAD_RECORDS__FAILED`, `LOAD_RECORDS__ENDED` | Track the lifecycle of batch loading operations |
| **Upsert or Load** | `UPSERT_OR_LOAD__START`, `UPSERT_OR_LOAD__DISTRIBUTED_LOCK_DETECTED`, `UPSERT_OR_LOAD__LOCAL_LOAD_IN_PROGRESS`, `UPSERT_OR_LOAD__BATCH__SUBSCRIBED`, `UPSERT_OR_LOAD__SINGLE__SUBSCRIBED`, `UPSERT_OR_LOAD__BATCH__SUCCEEDED`, `UPSERT_OR_LOAD__BATCH__FAILED`, `UPSERT_OR_LOAD__BATCH__ENDED`, `UPSERT_OR_LOAD__SINGLE__SUCCEEDED`, `UPSERT_OR_LOAD__SINGLE__FAILED`, `UPSERT_OR_LOAD__SINGLE__ENDED` | Monitor the smart upsert operation with collection state detection |

Events are published to `eventSubject` (a Reactor `Sinks.Many`) for subscription by monitoring systems.

## Vector Database Operation Scenarios

| Initial State | Trigger Action | Vector DB State | Locking Mechanism | Expected Outcome |
|---------------|----------------|-----------------|-------------------|------------------|
| App node starting | System initialization | DB has data (count > 0) | None | `loadRecordsIfEmpty` performs count check and determines no loading needed |
| App node starting | System initialization | DB is empty (count = 0) | Local flag + Distributed lock | `loadRecordsIfEmpty` triggers full loading; Local `loadInProgress` set to true; Distributed lock acquired; Records loaded sequentially; Locks released |
| Running system | Record update via internal `upsertRecord` | DB has data (count > 0) | None | Individual record updated without locking; Generates embedding and updates record |
| Running system | Record update via `upsertOrLoadRecords` | DB has data (count > 0) | None | System checks collection exists with data; Updates individual record without loading all |
| Running system | Record update via `upsertOrLoadRecords` | DB is empty (count = 0) | Local flag + Distributed lock | System detects empty collection; Sets local flag; Acquires distributed lock; Loads all records as batch; Locks released |
| Running system | Record update via `upsertOrLoadRecords` | Another node has distributed lock | Temporary local flag with timeout | System detects distributed lock; Sets local flag with 10-second timeout; Skips operation |
| Running system | Multiple record adds via `loadRecords` | DB has existing data | Local flag + Distributed lock | Tries to set local flag; Acquires distributed lock; Processes records sequentially with `concatMap`; Releases locks when done |
| Running system | Rebuild request | DB has existing data | Distributed lock | `rebuildIndex` acquires distributed lock; Deletes collection; Loads all records; Releases lock |
| Running system | Remove individual record | DB has existing data | None | `removeRecord` checks if collection exists; Removes single record by ID; No locks needed |
| Running system | Remove multiple records | DB has existing data | None | `removeRecords` processes deletion of multiple record IDs; No locks needed |
| Running system | Delete collection | DB has existing data | None | `deleteCollection` removes entire collection; No locks needed |
| Running system | Clear collection | DB has existing data | None | `clearCollection` removes all records but keeps collection structure; No locks needed |
| Running system | Namespace deletion | Multiple collections | Distributed lock | `deleteNamespace` acquires distributed lock; Deletes all collections in namespace; Releases lock |
| Node failure | Node crash during loading | Lock remains | Auto-expiration mechanism | Distributed lock has expiration timestamp and node ID information; Other nodes can take over after expiration |

## Key Implementation Details

1. **Sequential Processing with Reactor**:
   - Uses `concatMap` instead of `flatMap` for guaranteed sequential processing
   - Each record embedding and upserting is treated as one atomic unit
   - Comment in code explains: "parallel processing of these units fail to store records to the vector store, so concatMap is used to run 1 by 1"
   - All operations use `subscribeOn(Schedulers.boundedElastic())` to avoid blocking the main thread

2. **Smart Lock Detection and Management**:
   - `VectorDbLockManager` implements distributed locks using Qdrant collections
   - Locks include node identity, acquisition time, and expiration time
   - Temporary local flag with 10-second timeout set when distributed lock detected using `TimedExecutor.enableWithDuration`
   - Lock service availability check included (`isLockServiceAvailable`)
   - Locks auto-expire to prevent deadlocks if a node crashes (default is 5 minutes)

3. **Record Count and Collection Existence Handling**:
   - `qdrantClient.getRecordCount(params)` used to check if collection has data
   - `collectionAndIsReady` cache in `QdrantVectorDbClient` tracks collection readiness with timeout
   - System designed to handle potential drift between nodes
   - Auto-timeout mechanisms prevent deadlocks from node failures

4. **Distributed Processing Coordination**:
   - Multiple nodes can detect empty collections simultaneously
   - Only one node will successfully acquire the distributed lock
   - Other nodes will detect the lock and defer operations
   - Efficient coordination using minimal lock checks

5. **Comprehensive Event Tracking**:
   - Operations emit detailed events through `eventSubject` (`Sinks.many().multicast().onBackpressureBuffer()`)
   - Events use an enumerated type system (`VectorDbEvent.Type`) for consistent categorization
   - Events include specific state transitions (START, LOCK_ACQUIRED, SUCCEEDED, FAILED, ENDED)
   - Additional context for distributed operations (DISTRIBUTED_LOCK_DETECTED, LOCAL_LOAD_IN_PROGRESS)

6. **Optimized Collection Operations**:
   - `QdrantVectorDbClient` caches collection existence checks using `StatusMap` with cache duration
   - Smart upsert operation (`upsertOrLoadRecords`) handles both empty and populated collections
   - Vector validation ensures embedding quality before storage via `VectorDbVerifier`
   - Namespace operations efficiently manage multiple collections
   - Proper resource cleanup in `close()` methods

7. **Efficiency Optimizations**:
   - Local lock prevents redundant distributed lock checks
   - Distributed lock prevents duplicate initialization across nodes
   - Temporary lock flag with timeout prevents overloading lock service
   - `StatusMap` utility provides efficient caching with automatic timeouts
   - System designed to recover gracefully from node failures

8. **Error Handling and Diagnostics**:
   - Integration with diagnostics system via `VectorDbDiagnostics`
   - Operations include proper error handling with informative messages
   - Every major operation uses `doOnError` to report failures
   - Diagnostics can be enabled/disabled at runtime
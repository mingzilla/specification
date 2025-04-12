# Panintelligence AI Copilot Redis Integration Design

## Overview

This document outlines the design for implementing the AI Copilot functionality using Redis for event coordination while maintaining system resilience when Redis is temporarily unavailable.

## Design Principles

1. **Resilience**: System should continue functioning when Redis is down
2. **Efficiency**: Embedding computation should happen once per chart update, not per node
3. **Performance**: Vector queries should be served from local memory
4. **Eventual Consistency**: All nodes should eventually have complete vector data
5. **Simplicity**: Recovery mechanisms should be straightforward and self-healing

## Key Implementation Features

1. **Single Embedding Computation Per Chart**
   - Each chart embedding is computed exactly once, regardless of node count
   - The node that processes the chart update is responsible for the embedding
   - After computing, the embedding is distributed to all other nodes using Redis pub/sub feature

2. **Batch Embedding Coordination**
   - When batch embedding is in progress, other nodes are not allowed to perform embeddings
   - The `batchEmbeddingInProgress` flag in Redis prevents duplicate work
   - This flag has a timeout (e.g., 5 minutes) to prevent deadlocks if a node fails
   - If timeout expires, another node can take over the embedding process

3. **Local Vector Storage**
   - Each node maintains its own in-memory vector store for fast queries
   - No dependency on Redis for query operations
   - System continues to function when Redis is unavailable

4. **Redis Outage Handling**
   - No need to keep track of updated charts while Redis is down
   - A full vector rebuild is triggered and published to every node when Redis becomes available again

## Architecture Components

### 1. Vector Storage

- Each application node maintains its own in-memory vector store
- In-memory store provides fast local access for queries
- No direct dependency on Redis for vector storage

### 2. Redis Event Coordination

- Redis pub/sub used for broadcasting vector updates between nodes
- Events include chart ID, computed vector, and source node ID
- Publishing all vector records and publishing one vector record are 2 unique events
- Redis operations designed to be non-blocking with graceful error handling

### 3. Recovery Mechanism

- Self-detecting recovery when Redis becomes available
- Automatic full vector rebuild when Redis recovers
- Coordination flags stored in Redis itself to prevent duplicate rebuilds
- No critical functionality depends on Redis availability

## Chart Update Workflow

When a chart is updated, the system follows this workflow:

1. **Initial Checks**:
   - Check if `batchEmbeddingInProgress` flag is set in Redis
   - If true, skip the embedding process (another node is handling batch updates)

2. **Redis Recovery Check**:
   - Check if `redisWasDown` flag is set in Redis
   - This flag is only stored in Redis (set when Redis becomes available after being down)

3. **Action Based on Status**:
   - If `redisWasDown` is true:
     - Set `batchEmbeddingInProgress` flag with a 5-minute timeout
     - Run batch embedding, generating embeddings for all charts
     - Update the local vector store with all embeddings
     - Publish all embeddings to other nodes via Redis pub/sub
     - Set both `batchEmbeddingInProgress` and `redisWasDown` to false
   - If `redisWasDown` is false:
     - Generate embedding for only the updated chart
     - Update the local vector store
     - Publish the single embedding to other nodes via Redis pub/sub

4. **Error Handling**:
   - If Redis operations fail, local vector store is still updated
   - Next successful Redis operation will detect recovery and trigger rebuild

## Chart Vector Event Service

This service handles the coordination of vector updates between nodes:

```java
@Service
public class ChartVectorEventService {
    private static final String REDIS_WAS_DOWN_KEY = "vector:redis:was_down";
    private static final String BATCH_EMBEDDING_IN_PROGRESS_KEY = "vector:batch:in_progress";
    private static final Duration BATCH_TIMEOUT = Duration.ofMinutes(5); // 5 minute timeout to prevent deadlocks
    
    private final ReactiveRedisTemplate<String, ChartVectorEvent> redisTemplate;
    private final VectorDbService vectorDbService;
    private final ChartRepository chartRepository;
    private final Disposable subscription;
    
    // Initialize and subscribe to vector update events
    public ChartVectorEventService(ReactiveRedisTemplate<String, ChartVectorEvent> redisTemplate,
                                  VectorDbService vectorDbService,
                                  ChartRepository chartRepository) {
        this.redisTemplate = redisTemplate;
        this.vectorDbService = vectorDbService;
        this.chartRepository = chartRepository;
        this.subscription = subscribeToVectorUpdates();
    }
    
    // Listen for vector updates from other nodes
    private Disposable subscribeToVectorUpdates() {
        return redisTemplate.listenToChannel("chart-vector-updates")
            .onErrorContinue((error, obj) -> {
                log.warn("Error receiving vector update, will continue", error);
            })
            .map(message -> message.getMessage())
            .flatMap(event -> {
                // Skip our own events
                if (event.sourceNodeId.equals(getNodeId())) {
                    return Mono.empty();
                }
                
                // Add the vector to our local store
                return Mono.fromCallable(() -> {
                    vectorDbService.addVectorRecord(event.chartId, event.vector);
                    return true;
                });
            })
            .subscribe();
    }
    
    // Publish a vector update to other nodes
    public Mono<Void> publishVectorUpdate(Integer chartId, float[] vector) {
        // First check if batch process is running
        return redisTemplate.hasKey(BATCH_EMBEDDING_IN_PROGRESS_KEY)
            .flatMap(batchInProgress -> {
                if (batchInProgress) {
                    log.debug("Batch embedding in progress, skipping individual update");
                    return Mono.empty();
                }
                
                // Then check if Redis was down and needs recovery
                return redisTemplate.hasKey(REDIS_WAS_DOWN_KEY)
                    .flatMap(wasDown -> {
                        if (wasDown) {
                            log.info("Redis was down, initiating batch rebuild");
                            return startBatchRebuild();
                        } else {
                            // Normal operation - just publish this one update
                            ChartVectorEvent event = new ChartVectorEvent(chartId, vector, getNodeId());
                            return redisTemplate.convertAndSend("chart-vector-updates", event)
                                .doOnError(e -> {
                                    // Next successful connection will set this flag
                                    log.warn("Failed to publish vector update, Redis may be down", e);
                                })
                                .then();
                        }
                    })
                    .onErrorResume(e -> {
                        // If Redis check fails, set to true on next connection
                        log.warn("Failed to check Redis status, skipping publish", e);
                        return Mono.empty();
                    });
            })
            .onErrorResume(e -> {
                // If any Redis operation fails, it will be retried on next chart update
                log.warn("Redis appears to be down, skipping publish", e);
                return Mono.empty();
            });
    }
    
    // When Redis connection reestablished after outage
    private Mono<Void> startBatchRebuild() {
        // Set flag to prevent multiple nodes from rebuilding simultaneously
        return redisTemplate.opsForValue().setIfAbsent(BATCH_EMBEDDING_IN_PROGRESS_KEY, getNodeId(), BATCH_TIMEOUT)
            .flatMap(acquired -> {
                if (!acquired) {
                    log.info("Another node is already handling the rebuild");
                    return Mono.empty();
                }
                
                log.info("Starting full vector rebuild");
                
                // Fetch all charts and rebuild vectors
                return chartRepository.getAllCharts()
                    .collectList()
                    .flatMap(charts -> {
                        return Flux.fromIterable(charts)
                            .flatMap(chart -> generateEmbedding(chart)
                                .flatMap(vector -> {
                                    // Update local store
                                    vectorDbService.addVectorRecord(chart.getId(), vector);
                                    
                                    // Broadcast to other nodes
                                    ChartVectorEvent event = new ChartVectorEvent(chart.getId(), vector, getNodeId());
                                    return redisTemplate.convertAndSend("chart-vector-updates", event);
                                }))
                            .then();
                    })
                    .then(Mono.defer(() -> {
                        // Reset flags when complete
                        log.info("Vector rebuild complete");
                        return redisTemplate.delete(REDIS_WAS_DOWN_KEY)
                            .then(redisTemplate.delete(BATCH_EMBEDDING_IN_PROGRESS_KEY));
                    }));
            });
    }
    
    // Helper method to detect Redis recovery on reconnection
    public Mono<Boolean> checkAndMarkRedisRecovery() {
        // Called from a Redis connection listener
        return redisTemplate.opsForValue().set(REDIS_WAS_DOWN_KEY, "true");
    }
}
```

### Chart Deletion Service

This service handles the propagation of chart deletions to all nodes:

```java
@Service
public class ChartDeletionService {
    private static final String REDIS_WAS_DOWN_KEY = "vector:redis:was_down";
    
    private final ReactiveRedisTemplate<String, ChartDeletionEvent> redisTemplate;
    private final VectorDbService vectorDbService;
    private final Disposable subscription;
    
    // Subscribe to deletion events and process them
    private Disposable subscribeToChartDeletions() {
        return redisTemplate.listenToChannel("chart-deletions")
            .onErrorContinue((error, obj) -> {
                log.warn("Error processing chart deletion, will continue", error);
            })
            .map(message -> message.getMessage())
            .flatMap(event -> {
                // Skip our own events
                if (event.sourceNodeId.equals(getNodeId())) {
                    return Mono.empty();
                }
                
                // Remove the chart from local vector store
                return Mono.fromCallable(() -> {
                    vectorDbService.removeRecord(event.chartId);
                    return true;
                });
            })
            .subscribe();
    }
    
    // Publish a chart deletion to all nodes
    public Mono<Void> publishChartDeletion(Integer chartId) {
        ChartDeletionEvent event = new ChartDeletionEvent(chartId, getNodeId());
        
        return redisTemplate.convertAndSend("chart-deletions", event)
            .doOnError(e -> {
                log.warn("Failed to publish chart deletion, will be handled during next rebuild", e);
                // No need to track this specifically - the next rebuild will clean it up
            })
            .then();
    }
}
```

### Vector Synchronization Service

This service ensures all nodes eventually have complete vector data through periodic syncs:

```java
@Service
public class VectorSyncService {
    private final VectorDbService vectorDbService;
    private final ChartRepository chartRepository;
    private final ReactiveRedisTemplate<String, Object> redisTemplate;
    
    private static final String BATCH_EMBEDDING_IN_PROGRESS_KEY = "vector:batch:in_progress";
    private static final Duration BATCH_TIMEOUT = Duration.ofMinutes(5); // 5 minute timeout
    
    // Scheduled full sync (hourly) - fallback mechanism
    @Scheduled(fixedRate = 3600000)
    public void performScheduledSync() {
        // Only perform if not already in progress
        redisTemplate.hasKey(BATCH_EMBEDDING_IN_PROGRESS_KEY)
            .flatMap(inProgress -> {
                if (inProgress) {
                    log.info("Batch embedding already in progress, skipping scheduled sync");
                    return Mono.empty();
                }
                
                log.info("Starting scheduled vector sync");
                return initiateFullSync();
            })
            .subscribe(
                result -> {},
                error -> log.error("Error during scheduled sync check", error)
            );
    }
    
    public Mono<Void> initiateFullSync() {
        // Set flag to prevent multiple nodes from rebuilding simultaneously
        return redisTemplate.opsForValue().setIfAbsent(BATCH_EMBEDDING_IN_PROGRESS_KEY, getNodeId(), BATCH_TIMEOUT)
            .flatMap(acquired -> {
                if (!acquired) {
                    log.info("Another node is already handling the sync");
                    return Mono.empty();
                }
                
                return chartRepository.getAllCharts()
                    .collectList()
                    .flatMap(charts -> vectorDbService.rebuildVectorStore(charts))
                    .doOnSuccess(count -> log.info("Vector sync completed, processed {} charts", count))
                    .doOnError(error -> log.error("Error during vector sync", error))
                    .then(redisTemplate.delete(BATCH_EMBEDDING_IN_PROGRESS_KEY));
            });
    }
}
```

## Redis Recovery Mechanism

1. **Redis Unavailability Handling**:
   - All Redis operations are wrapped with `onErrorResume` to prevent failures
   - Local vector operations continue to function without disruption
   - No tracking of individual changes needed while Redis is down

2. **Recovery Detection**:
   - Recovery detected naturally during chart update operations
   - When Redis becomes available after being down, set `redisWasDown` flag in Redis
   - Flag checked on each chart update operation

3. **Rebuild Process**:
   - First node to detect recovery initiates rebuild with atomic Redis operation
   - Batch rebuild is coordinated with flags in Redis
   - After completion, flags are cleared automatically
   - Time-based lock expiration provides self-healing

## Redis Connection Management

```java
@Configuration
public class RedisConnectionListener {
    private final ChartVectorEventService chartVectorEventService;
    
    @EventListener(RedisConnectionFailureEvent.class)
    public void onConnectionFailure(RedisConnectionFailureEvent event) {
        log.warn("Redis connection failure detected");
    }
    
    @EventListener(RedisConnectedEvent.class)
    public void onConnectionRestored(RedisConnectedEvent event) {
        log.info("Redis connection restored, marking for vector rebuild");
        
        // Mark that Redis was down, so next chart update will trigger rebuild
        chartVectorEventService.checkAndMarkRedisRecovery()
            .subscribe(
                result -> log.info("Redis recovery flag set: {}", result),
                error -> log.error("Failed to set Redis recovery flag", error)
            );
    }
}
```

## Implementation Plan

1. **Phase 1: Redis Infrastructure**
   - Add Redis configuration
   - Create event model classes
   - Implement basic pub/sub capabilities

2. **Phase 2: Vector Update Coordination**
   - Implement ChartVectorEventService with recovery detection
   - Integrate with existing vector generation flow
   - Add automatic rebuild mechanism

3. **Phase 3: Chart Deletion Coordination**
   - Implement ChartDeletionService
   - Connect to chart deletion workflow
   - Test multi-node deletion propagation

4. **Phase 4: Diagnostics & Admin UI**
   - Add configuration toggles for Redis features
   - Implement diagnostics endpoints
   - Create admin UI components

## Monitoring Considerations

1. **Redis Health Metrics**:
   - Connection status
   - Publication success rate
   - Subscription activity

2. **Synchronization Metrics**:
   - Last successful full sync timestamp
   - Vector count per node
   - Batch rebuild frequency

3. **Alert Conditions**:
   - Redis unavailability exceeding configured threshold
   - Batch rebuild taking longer than expected
   - Vector store inconsistency detected
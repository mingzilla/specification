# L1 Caching System Specification

## 1. System Overview

The L1 Caching System is designed for a multi-node web application that needs efficient caching of domain objects while maintaining data consistency in a load-balanced environment without sticky sessions.

### 1.1 Core Design Principles

- **Two-Tier Caching**: Short-term cache (seconds) for rate limiting and long-term cache (minutes) for performance
- **Request Coalescing**: Only one database request per key, with concurrent requests for the same key queued
- **Reactive Invalidation**: No proactive cache invalidation; instead, validate cache freshness on access
- **Load Balancing Support**: Functions correctly across multiple application nodes without coordination
- **Thread Safety**: Fully thread-safe with minimal contention

### 1.2 Key Business Requirements

- Reduce database load for frequently accessed data
- Prevent duplicate requests from hitting the database in high-concurrency scenarios
- Support display-oriented features where perfect real-time data is not critical
- Function correctly in a multi-node, load-balanced environment without sticky sessions
- Maintain eventual consistency without explicit cache coordination

## 2. Architecture Components

### 2.1 Core Cache Components

1. **ExpirableObject<T>**
   - Stores a single cached value with expiration metadata
   - Tracks last access time for optional time extension
   - Provides atomic expiration checking and value retrieval
   - Supports caching of any Java object type through generics

2. **ExpirableObjectMap<T>**
   - Thread-safe collection of ExpirableObject instances
   - Maps string keys to ExpirableObject instances
   - Provides per-key locking for concurrent access
   - Handles cache access, creation, and expiration

3. **ExpirableLongLifeCache<CheckerT, CacheT>**
   - Implements the two-tier caching strategy
   - Uses a fast "checker" cache (short lifetime) to determine if the main data cache is still valid
   - Uses a slow "data" cache (long lifetime) for the actual domain objects
   - Implements request coalescing via per-key locks
   - Supports custom cache expiration strategies

4. **CacheExpiryCondition<CheckerT, CacheT>**
   - Strategy interface for custom cache validation logic
   - Compares cached item metadata with fresh metadata to determine validity
   - Allows domain-specific cache invalidation rules

5. **ConcurrentLockUtil**
   - Utility for managing thread synchronization
   - Provides per-key locking mechanisms
   - Ensures correct lock acquisition and release even during exceptions

### 2.2 Cache Hierarchy

```
ExpirableLongLifeCache
├── checkerCache (ExpirableObjectMap<CheckerT>)
│   └── Contains ExpirableObject<CheckerT> instances
├── actualDataCache (ExpirableObjectMap<CacheT>)
│   └── Contains ExpirableObject<CacheT> instances
└── locks (ConcurrentHashMap<String, Lock>)
```

## 3. Core Functionality

### 3.1 Cache Access Flow

1. Client requests an item by key
2. System acquires a lock for that key
3. System checks the short-lived checker cache:
   - If checker data is valid, proceed to step 5
   - If checker data is expired, fetch fresh checker data from source
4. System decides whether to invalidate the long-lived data cache:
   - Compare cached metadata with fresh metadata using CacheExpiryCondition
   - If expired, remove the data from long-lived cache
5. System checks the long-lived data cache:
   - If data is present and valid, return it
   - If data is missing or was invalidated, fetch fresh data from source
6. System releases the lock for that key
7. Client receives the requested item

### 3.2 Cache Invalidation Strategy

- **No proactive invalidation** - Never directly invalidate cache when data changes
- **No deletion handling needed** - When an item is deleted from the database, there's no need to explicitly remove it from the cache. This will be automatically handled during the cache validation step when the checker returns null
- **Load balancer compatibility** - In a load-balanced environment without sticky sessions, proactive cache invalidation is ineffective as it would only affect the current node. The reactive approach ensures all nodes eventually see consistent data
- **Reactive validation** - Check data freshness on each cache access
- **Timestamp-based validation** - Compare `updatedAtMs` timestamps between cached and fresh data
- **Hierarchical validation** - Check both primary and parent objects for changes
- **Custom validation logic** - Allow domain-specific expiration rules via CacheExpiryCondition

### 3.3 Concurrency Control

- **Per-key locking** - Separate locks for different cache keys
- **Request coalescing** - Multiple requests for the same key are processed sequentially
- **Lock scope limitation** - Locks are held only for the duration of cache validation and potential refresh
- **Cache-level operations** - Thread-safe map implementations for all cache collections

### 3.4 Metadata Requirements

The caching system relies on specific metadata in domain objects to function correctly:

- **updatedAtMs (critical)** - Every domain object that serves as a checker or as part of a domain bundle must have an `updatedAtMs` timestamp field
- This timestamp should be automatically updated whenever the object is modified
- The timestamp serves as the primary mechanism for determining cache validity
- For hierarchical objects (e.g., parent-child relationships), both objects' timestamps must be compared
- The `updatedAtMs` field should be a long value representing milliseconds since epoch for precise comparisons
- Database triggers or ORM lifecycle hooks should ensure this field is always updated correctly

Example cache validation using updatedAtMs:
```java
boolean isExpired = freshChecker.getUpdatedAtMs() > cachedData.getDataSourceItem().getUpdatedAtMs();
```

This single field is essential for the reactive validation strategy, as it provides a simple, reliable way to detect changes without requiring complex object comparisons.

## 4. Technical Requirements

### 4.1 Java Implementation

- Java 17 or higher (required)
- Caffeine cache as the underlying caching mechanism
- Thread-safe implementation of all components
- Support for generics to handle different data types
- Exception-safe design for all public methods
- Prefer Java records over classes wherever appropriate for immutable data structures
- Leverage Java 17+ features such as pattern matching, enhanced switch expressions, and sealed classes where appropriate
- Use modern Java idioms including functional interfaces and the Stream API

Records are especially well-suited for:
- Domain transfer objects
- Cache metadata wrappers
- Configuration objects
- Immutable checker objects

```java
// Example using Java record for cache configuration
public record CacheConfig(
    int checkerCacheSeconds,
    int dataCacheSeconds,
    long maximumSize,
    boolean extendLifetime
) {}

// Example using record for a checker object
public record DataSourceChecker(
    Long id,
    long updatedAtMs,
    String name
) {}
```

### 4.2 Core Interfaces

```java
public interface CacheExpiryCondition<C, T> {
    /**
     * Determines if the cached data can still be used when the checker has expired
     * 
     * @param cachedCheckerItem Previously cached checker item
     * @param freshCheckerItem Newly fetched checker item from data source
     * @param cachedDataItem Currently cached data item
     * @return true if the cached data is still valid, false if it should be refreshed
     */
    boolean canStillUseCacheWhenCheckerExpires(
        ExpirableObject<C> cachedCheckerItem, 
        C freshCheckerItem, 
        ExpirableObject<T> cachedDataItem
    );
}

public interface ExpirableCache<T> {
    /**
     * Gets an object from the cache or fetches it using the provided function
     * 
     * @param key Cache key
     * @param fetchFn Function to fetch the object if not in cache
     * @return The cached or freshly fetched object
     */
    T getOrFetch(String key, Supplier<T> fetchFn);
    
    /**
     * Removes an object from the cache
     * 
     * @param key Cache key
     */
    void removeCache(String key);
    
    /**
     * Empties the entire cache
     */
    void emptyCache();
    
    /**
     * Checks if the cache is empty
     * 
     * @return true if the cache is empty, false otherwise
     */
    boolean isEmpty();
}

public interface ExpirableLongLifeCacheInterface<C, T> {
    /**
     * Gets an object from the two-tier cache or fetches it using the provided functions
     * 
     * @param key Cache key
     * @param fetchCheckerFn Function to fetch the checker object
     * @param createExpiryConditionFn Function to create the expiry condition
     * @param fetchDataFn Function to fetch the data object
     * @return The cached or freshly fetched data object
     */
    T getOrFetch(
        String key,
        Supplier<C> fetchCheckerFn,
        Supplier<CacheExpiryCondition<C, T>> createExpiryConditionFn,
        Supplier<T> fetchDataFn
    );
}
```

### 4.3 Performance Requirements

- Minimal lock contention for different keys
- Efficient memory usage with appropriate cache size limits
- Fast cache access (<1ms) for cached items
- Support for high concurrency (hundreds of simultaneous requests)
- Graceful degradation under extreme load

## 5. Usage Patterns

### 5.1 When to Use

- Display-oriented features where real-time data is not critical
- Areas with potential concurrent requests for the same data
- Read-heavy application sections where data changes infrequently
- Rate-limiting database access for frequently requested items
- Dashboards, reports, and other read-heavy UI components

### 5.2 When Not to Use

- Editing features where real-time data is essential
- API endpoints requiring the latest data
- Data export/import functionality
- Areas where data consistency is more important than performance
- Transaction-heavy operations where data integrity is critical

### 5.3 Typical Use Cases

- **Chart and Dashboard Rendering**: Caching data connections, chart definitions, and category information
- **Dropdown and Autocomplete Data**: Caching reference data used in UI components
- **User Permission Data**: Caching frequently accessed, rarely changed authorization data
- **Metadata for UI Components**: Caching column definitions, display formats, and other UI configuration

## 6. Implementation Considerations

### 6.1 Caffeine Integration

**Current shortcoming:**
The existing implementation uses custom cache maps with manual expiration logic.

**Potential solution:**
- Use Caffeine's `AsyncLoadingCache` for the data cache
- Configure appropriate expiration policies (time-based for checker cache)
- Use Caffeine's statistics for monitoring cache performance
- Leverage Caffeine's eviction policies for memory management

```java
// Sample Caffeine configuration
Cache<String, ExpirableObject<T>> caffeineCache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .recordStats()
    .build();
```

### 6.2 Thread Safety Improvements

**Current shortcoming:**
The current implementation has no mechanism to handle lock timeouts or prevent stuck locks if a thread crashes while holding a lock.

**Potential solution:**
- Use `StampedLock` for read-write locking with better performance
- Implement lock timeout mechanisms to prevent indefinite blocking
- Add proper exception handling in all lock-related operations
- Implement mechanism to detect and clean up idle locks

```java
// Sample lock usage with timeout and try-finally
Lock lock = getLock(key);
boolean acquired = false;
try {
    acquired = lock.tryLock(timeoutMs, TimeUnit.MILLISECONDS);
    if (!acquired) {
        // Return stale data or null on timeout
        logger.warn("Lock acquisition timeout for key: {}", key);
        return dataCache.getIfPresent(key);
    }
    
    // Cache operations
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    return dataCache.getIfPresent(key);
} finally {
    if (acquired) {
        lock.unlock();
    }
}
```

### 6.3 Memory Management

**Current shortcoming:**
The current implementation has no maximum size limits for caches, which could lead to unbounded memory growth, especially if many unique keys are accessed.

**Potential solution:**
- Add configurable maximum size limits based on real usage patterns
- Implement least-recently-used eviction when size limits are reached
- Add expiration policies as a safety valve for rarely accessed entries
- Periodically clean up unused locks and cache entries

```java
// Size + time-based approach
Cache<String, T> cache = Caffeine.newBuilder()
    .maximumSize(10000)  // Set based on monitoring data
    .expireAfterAccess(2, TimeUnit.HOURS)  // Safety net for rarely used entries
    .build();
```

This approach balances keeping useful data cached while preventing unbounded growth. Since the data being cached is likely to be reused, generous size limits with a long access-based expiration can provide a good compromise.

### 6.4 Monitoring and Metrics

**Current shortcoming:**
The current implementation doesn't include built-in metrics or monitoring capabilities, making it difficult to observe cache performance and optimize settings.

**Potential solution:**
- Implement cache statistics collection for hit/miss rates
- Add monitoring for cache size and memory usage
- Track lock contention and acquisition times
- Measure average fetch latency for cache misses
- Expose metrics through application monitoring system

```java
// Enable stats recording in Caffeine
Cache<String, T> cache = Caffeine.newBuilder()
    .recordStats()
    .build();

// Access and log stats periodically
CacheStats stats = cache.stats();
logger.info("Cache metrics - Hit rate: {}, Avg load: {}ms, Size: {}", 
    stats.hitRate(), 
    stats.averageLoadPenalty()/1_000_000,
    cache.estimatedSize());
```

These metrics would help tune the cache configuration and quantify its benefits in production.

## 7. Sample Implementation

### 7.1 Core Class Structure

**Current design:**
The current structure consists of three main classes with distinct responsibilities. When implementing with Caffeine, this structure could be simplified while maintaining the core functionality.

```java
public class ExpirableObject<T> {
    private T value;
    private long lastAccessTime;
    private final int lifetimeSeconds;
    private final boolean extendLifetime;
    
    // Methods for checking expiration and accessing value
}

public class ExpirableObjectMap<T> {
    private final ConcurrentHashMap<String, ExpirableObject<T>> cache;
    private final ConcurrentHashMap<String, Lock> locks;
    private final int lifetimeSeconds;
    private final boolean extendLifetime;
    
    // Methods for thread-safe cache access
}

public class ExpirableLongLifeCache<C, T> {
    private final ExpirableObjectMap<C> checkerCache;
    private final ExpirableObjectMap<T> dataCache;
    private final ConcurrentHashMap<String, Lock> locks;
    
    // Methods for two-tier caching
}
```

**Potential simplified structure with Caffeine:**
```java
public class TwoTierCache<C, T> {
    private final Cache<String, C> checkerCache;
    private final Cache<String, T> dataCache;
    private final ConcurrentHashMap<String, Lock> locks = new ConcurrentHashMap<>();
    
    // The core method preserving the three-step approach
    public T getOrFetch(String key, 
                       Function<String, C> fetchChecker,
                       BiFunction<C, T, Boolean> isDataValid,
                       Function<String, T> fetchData) {
        Lock lock = getLock(key);
        lock.lock();
        try {
            // 1. Short-term checker cache
            C checker = checkerCache.get(key, k -> fetchChecker.apply(k));
            if (checker == null) {
                dataCache.invalidate(key);
                return null;
            }
            
            // 2. Expiry check
            T cachedData = dataCache.getIfPresent(key);
            if (cachedData != null && !isDataValid.apply(checker, cachedData)) {
                dataCache.invalidate(key);
                cachedData = null;
            }
            
            // 3. Long-term data cache
            if (cachedData == null) {
                cachedData = fetchData.apply(key);
                if (cachedData != null) {
                    dataCache.put(key, cachedData);
                }
            }
            
            return cachedData;
        } finally {
            lock.unlock();
        }
    }
}
```

This simplified structure maintains the three-step approach (short-term cache, expiry check, long-term cache) while leveraging Caffeine's built-in capabilities.

### 7.2 Typical Usage Example

```java
// Create cache with 5-second checker lifetime and 50-minute data lifetime
TwoTierCache<List<DataSourceItem>, ColumnBundle> cache = 
    new TwoTierCache<>(
        Caffeine.newBuilder().expireAfterWrite(5, TimeUnit.SECONDS).build(),
        Caffeine.newBuilder().expireAfterAccess(50, TimeUnit.MINUTES).build()
    );

// Define data validation function
BiFunction<List<DataSourceItem>, ColumnBundle, Boolean> isDataValid = 
    (checkers, bundle) -> {
        // Primary item validation
        if (checkers.isEmpty() || bundle.getDataSourceItem() == null) {
            return false;
        }
        
        // Check if primary item has been updated
        boolean primaryItemExpired = checkers.get(0).updatedAtMs() > 
                                    bundle.getDataSourceItem().getUpdatedAtMs();
        
        // Check if parent item has been updated (if applicable)
        boolean parentItemExpired = false;
        if (checkers.size() > 1 && checkers.get(1) != null && 
            bundle.getParentDataSourceItem() != null) {
            parentItemExpired = checkers.get(1).updatedAtMs() > 
                               bundle.getParentDataSourceItem().getUpdatedAtMs();
        }
        
        // Cache is valid only if neither item has expired
        return !primaryItemExpired && !parentItemExpired;
    };

// Use cache in a service
public ColumnBundle getBundle(Integer dataSourceItemId) {
    if (dataSourceItemId == null) {
        return ColumnBundle.empty();
    }
    
    return cache.getOrFetch(
        dataSourceItemId.toString(),
        // Fast checker function - gets minimal data to check freshness
        id -> dataSourceItemRepository.findCurrentAndParentById(Long.parseLong(id)),
        // Data validation function
        isDataValid,
        // Slow data function - gets full data bundle
        id -> columnBundleService.fetchBundle(Long.parseLong(id))
    );
}
```

## 8. Known Limitations and Considerations

1. **No Distributed Cache Coordination**
   - Each node maintains its own cache
   - No communication between nodes about cache invalidation
   - Consider distributed cache solutions (like Redis) if strict consistency is required

2. **Data Freshness**
   - Potential for slightly stale data if changes occur on different nodes
   - Maximum staleness is limited by the checker cache lifetime
   - Trade-off between performance and perfect consistency

3. **Cache Cleanup**
   - No automatic cleanup of expired entries - relies on access patterns
   - Current design has scheduled cleanup methods (`emptyCache()`) that run periodically (short-term cache every 5 minutes, long-term cache every hour)
   - Consider adding more targeted cleanup strategies beyond full cache invalidation

4. **Lock Management**
   - Lock creation is unbounded if many unique keys are accessed
   - Consider implementing lock cleanup for inactive keys
   - Monitor lock contention in high-concurrency scenarios

5. **Error Handling**
   - Must ensure locks are released even during exceptions
   - Cache refresh failures should not block access to stale data
   - Consider fallback mechanisms for critical cache failures

## 9. Migration and Testing Strategy

### 9.1 Migration from Groovy to Java

1. **Structural Equivalence**
   - Maintain the same class structure and responsibilities
   - Ensure all public methods have identical signatures
   - Preserve thread safety guarantees

2. **Java-Specific Improvements**
   - Use Java's stronger type system
   - Replace Groovy dynamic features with explicit Java equivalents
   - Leverage Java's functional interfaces for closures

3. **Caffeine Integration**
   - Replace custom cache maps with Caffeine caches
   - Adapt the timing mechanisms to use Caffeine's expiration
   - Maintain the two-tier cache architecture

### 9.2 Testing Strategy

1. **Unit Tests**
   - Test each component in isolation
   - Use mock objects for dependencies
   - Test thread safety with concurrent test cases

2. **Integration Tests**
   - Test the complete cache system with real data sources
   - Verify correct behavior in multi-threaded scenarios
   - Test performance under load

3. **Key Test Scenarios**
   - Cache hit/miss behavior
   - Expiration and refresh logic
   - Concurrent access to same key
   - Concurrent access to different keys
   - Recovery from exceptions
   - Memory usage under load
   - Force fetch functionality

4. **Cleanup Testing**
   - Test periodic cache cleanup functionality
   - Verify memory usage before and after cleanup
   - Ensure locks are properly released after cleanup

## 10. Additional Requirements

### 10.1 Force Fetch Functionality

**Requirement:**
The system occasionally needs to explicitly force data retrieval from the database, bypassing all caching. This typically happens when data is known to have been updated (e.g., when a data connection is modified).

**Key characteristics:**
- When a `forceFetch` flag is set to true, both short-term and long-term caches should be bypassed
- These force fetch requests are infrequent and never concurrent for the same ID
- The system would never have multiple simultaneous requests with the same ID and the force fetch flag set

**Potential implementation:**
```java
public T getOrFetch(String key, boolean forceFetch, /* other parameters */) {
    if (forceFetch) {
        // Clear both caches under lock to prevent race conditions
        Lock lock = getLock(key);
        lock.lock();
        try {
            checkerCache.invalidate(key);
            dataCache.invalidate(key);
        } finally {
            lock.unlock();
        }
    }
    
    // Proceed with normal fetch logic
    return getOrFetch(key, /* other parameters */);
}
```

This approach ensures that when `forceFetch` is true, fresh data is always retrieved from the database.

## 11. Conclusion

The L1 Caching System provides a robust, thread-safe caching solution for multi-node applications with specific focus on request coalescing and reactive cache validation. By migrating from Groovy to Java and leveraging Caffeine, the system will benefit from improved performance, better memory management, and enhanced monitoring capabilities while maintaining the core functionality that solves the business requirements.

The design prioritizes performance while ensuring data consistency through its reactive validation approach, making it well-suited for read-heavy distributed applications where absolute real-time consistency is less critical than system performance.
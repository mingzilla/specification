# Component Diagnostics Utility Specification

## Overview
A diagnostic utility that serves as a single source of truth for troubleshooting specific system components. It provides real-time monitoring, error tracking, and actionable recommendations without requiring log file analysis. Each component in the system can have its own dedicated diagnostic utility, making problem identification immediate and targeted.

## Background and Goals

### Problem Statement
Traditional logging systems often fall short when troubleshooting specific components:
- Log files contain mixed information from many components, making it difficult to isolate issues
- Logs focus on recording events but lack actionable recommendations
- Test teams without deep system knowledge struggle to interpret raw logs
- Determining if a problem is due to user error or system failure requires expertise
- Configuration issues are particularly difficult to diagnose from logs alone

### Primary Goals
This diagnostic utility design aims to:
1. Provide immediate answers to "why isn't this working?" without log analysis
2. Enable non-developers to self-diagnose and resolve common issues
3. Reduce troubleshooting time through component-specific diagnostics
4. Offer clear, actionable recommendations tied to specific error conditions
5. Minimize memory impact by being explicitly enabled only when needed

## Typical Use Cases

### Configuration Validation
**Scenario**: "The vector DB doesn't work. Is my configuration correct? How can I fix it?"

**How the utility helps**:
- Records configuration parameters when components are initialized
- Flags misconfigurations with specific error messages
- Provides concrete suggestions for configuration corrections
- Shows current configuration values alongside expected formats

```
Error Summary:
[ERROR] Vector store initialization failed: Invalid embedding URL format http:/localhost:11434 (missing slash)
First seen: 2023-06-04T14:24:32Z
Recommended Action: Correct the embedding service URL to include double slashes (http://localhost:11434)
```

### State Verification
**Scenario**: "Is the vector DB working? Does it have any data stored?"

**How the utility helps**:
- Records component initialization status
- Tracks record counts and data operation metrics
- Reports when expected data is missing
- Shows when components are properly initialized but empty

```
Metrics:
vectorstore.records                : 0
vectorstore.inserts                : 0
vectorstore.searches               : 3

Error Summary:
[ERROR] Search returned no results: Vector store contains no records
First seen: 2023-06-04T14:35:12Z
Recommended Action: Initialize the vector store with data before searching
```

### Functionality Verification
**Scenario**: "Is embedding working? How do I know if it works or not?"

**How the utility helps**:
- Tracks success/failure rates for key operations
- Records timing metrics to identify performance issues
- Captures specific error conditions with technical details
- Shows connectivity and dependency status

```
Metrics:
embedding.requests                 : 15
embedding.failures                 : 15
embedding.duration                 : avg=0.00ms min=0ms max=0ms

Error Summary:
[ERROR] Embedding generation failed: Connection refused to http://localhost:11434 (15 occurrences)
First seen: 2023-06-04T14:40:01Z
Last seen: 2023-06-04T14:45:32Z
Recommended Action: Check if Ollama service is running at http://localhost:11434
```

### Root Cause Analysis
**Scenario**: "Why do I not get any data back? Is it me being wrong or is it because the system is wrong?"

**How the utility helps**:
- Correlates user inputs with system responses
- Identifies whether failures are due to user error or system issues
- Clearly distinguishes between "no results" and "error conditions"
- Provides specific recommendations based on the root cause

```
Metrics:
vectorstore.records                : 1250
vectorstore.inserts                : 1250
vectorstore.searches               : 5
search.zero_results                : 5

Recent Events:
[2023-06-04T15:01:23Z] SEARCH_COMPLETED - Query "quantum computer sales" returned 0 results with similarity threshold 0.75
Recommended Action: No matching records found. Try broadening your search terms or reducing the similarity threshold.
```

## Usage Patterns

### For Test Teams
- Enable diagnostics before starting a test scenario: `{Component}Diagnostics.enable()`
- Run the test scenario that exhibits the problematic behavior
- When encountering unexpected behavior, call `{Component}Diagnostics.getStatus()` to receive a complete diagnostic report
- Follow the recommended actions without requiring developer assistance
- Disable diagnostics when finished to free memory: `{Component}Diagnostics.disable()`
- Use as first line of investigation when troubleshooting component-specific issues

### For Developers
- Instrument code with diagnostic events at key decision points and error conditions
- Include current configuration state with errors for complete context
- Provide specific troubleshooting steps for common failure modes
- Implement one diagnostic utility per major system component

### For Operations
- Monitor component health by periodically checking diagnostic status
- Identify recurring issues through operation metrics
- Reset diagnostics after maintenance activities
- Use as a quick health check during system verification

## Core Features

### 1. Event Tracking
- Maintains a bounded collection of the most recent system events (default: 100 events maximum)
- Each event includes a timestamp, type, message, and optional recommendation
- New events are added at the beginning of the collection
- When maximum capacity is reached, the oldest events are automatically removed
- Groups similar errors by "error signature" with occurrence counts and timestamps
- Tracks first and last occurrence times for each unique error
- Captures configuration state with each significant change or error
- Collects operation metrics (counts, timing statistics)
- Tracks failures with detailed context for troubleshooting

### 2. State Management
- Enable/disable functionality to control memory usage
- When disabled, all data structures are cleared to free memory
- When enabled, initializes tracking structures for capturing diagnostic data
- Thread-safe state transitions using atomic operations

### 3. Status Reporting
- Current configuration
- Error summary with grouped occurrences and recommendations
- Regular events (non-error) in chronological order
- Operation statistics with counts, averages, min/max values
- System state information

## Implementation Structure

### Base Class
```java
public class {Component}Diagnostics {
    private static final int MAX_EVENTS = 100;
    private static final ConcurrentHashMap<String, LongAdder> counters = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, TimingStats> timers = new ConcurrentHashMap<>();
    private static final List<DiagnosticEvent> events = new ArrayList<>();
    private static final Map<String, ErrorStats> errorStats = new ConcurrentHashMap<>();
    private static final AtomicBoolean enabled = new AtomicBoolean(false);
    private static final Logger logger = LoggerFactory.getLogger({Component}Diagnostics.class);
    
    private {Component}Diagnostics() {
        // Prevent instantiation
    }
    
    public static void enable() {
        if (enabled.compareAndSet(false, true)) {
            logger.info("{Component} diagnostics enabled");
        }
    }
    
    public static void disable() {
        if (enabled.compareAndSet(true, false)) {
            clearDiagnostics();
            logger.info("{Component} diagnostics disabled");
        }
    }
    
    public static boolean isEnabled() {
        return enabled.get();
    }
    
    // Method to record component state information
    public static void recordComponentState(String component, String state, int recordCount) {
        if (!isEnabled()) {
            return;
        }
        
        // Record current state
        addEvent(new DiagnosticEvent(
            "STATE_INFO",
            String.format("%s current state: %s, records: %d", component, state, recordCount),
            recordCount == 0 ? String.format("%s is initialized but contains no data", component) : null
        ));
        
        // Update counters
        increment(component.toLowerCase() + ".records", recordCount);
    }
    
    // Method to record search results with recommendations for zero results
    public static void recordSearchResults(String query, int resultCount, float similarityThreshold) {
        if (!isEnabled()) {
            return;
        }
        
        // Record the search event
        String message = String.format("Query \"%s\" returned %d results with similarity threshold %.2f", 
            query, resultCount, similarityThreshold);
        String recommendation = null;
        
        // Add recommendations for zero results
        if (resultCount == 0) {
            increment("search.zero_results");
            recommendation = "No matching records found. Try broadening your search terms or reducing the similarity threshold.";
        }
        
        addEvent(new DiagnosticEvent(
            "SEARCH_COMPLETED",
            message,
            recommendation
        ));
    }
}
```

### Key Supporting Classes

#### DiagnosticEvent
```java
private static class DiagnosticEvent {
    private final String type;
    private final String message;
    private final String recommendation;
    private final Instant timestamp;

    DiagnosticEvent(String type, String message, String recommendation) {
        this.type = type;
        this.message = message;
        this.recommendation = recommendation;
        this.timestamp = Instant.now();
    }

    @Override
    public String toString() {
        return String.format("[%s] %s - %s", timestamp, type, message);
    }
}
```

#### ErrorStats
```java
private static class ErrorStats {
    private final AtomicInteger occurrences = new AtomicInteger(0);
    private final Instant firstSeen;
    private volatile Instant lastSeen;
    private final String message;
    private final String recommendation;
    
    public ErrorStats(String message, String recommendation) {
        this.message = message;
        this.recommendation = recommendation;
        this.firstSeen = Instant.now();
        this.lastSeen = firstSeen;
    }
    
    public void recordOccurrence() {
        occurrences.incrementAndGet();
        lastSeen = Instant.now();
    }
    
    public int getOccurrences() {
        return occurrences.get();
    }
    
    public Instant getFirstSeen() {
        return firstSeen;
    }
    
    public Instant getLastSeen() {
        return lastSeen;
    }
    
    public String getMessage() {
        return message;
    }
    
    public String getRecommendation() {
        return recommendation;
    }
}
```

#### TimingStats
```java
private static class TimingStats {
    private final LongAdder count = new LongAdder();
    private final LongAdder totalTime = new LongAdder();
    private final AtomicLong minTime = new AtomicLong(Long.MAX_VALUE);
    private final AtomicLong maxTime = new AtomicLong(0);

    public void record(long durationMs) {
        count.increment();
        totalTime.add(durationMs);
        
        // Update min time (using CAS to avoid race conditions)
        long currentMin = minTime.get();
        while (durationMs < currentMin) {
            if (minTime.compareAndSet(currentMin, durationMs)) {
                break;
            }
            currentMin = minTime.get();
        }
        
        // Update max time (using CAS to avoid race conditions)
        long currentMax = maxTime.get();
        while (durationMs > currentMax) {
            if (maxTime.compareAndSet(currentMax, durationMs)) {
                break;
            }
            currentMax = maxTime.get();
        }
    }

    public double getAverageMs() {
        long currentCount = count.sum();
        return currentCount > 0 ? (double) totalTime.sum() / currentCount : 0.0;
    }
    
    public long getMinMs() {
        return minTime.get() == Long.MAX_VALUE ? 0 : minTime.get();
    }
    
    public long getMaxMs() {
        return maxTime.get();
    }
}
```

### Common Methods

#### Configuration Recording
```java
public static void record{Component}Configuration({Config} config) {
    if (!isEnabled()) {
        return;
    }
    addEvent(new DiagnosticEvent(
        "CONFIGURATION",
        formatConfigMessage(config),
        null
    ));
}

private static String formatConfigMessage({Config} config) {
    return String.format("{Component} configuration - Parameter1: %s, Parameter2: %s",
        config.getParameter1(), config.getParameter2());
}
```

#### Operation Recording
```java
public static void record{Operation}(String details) {
    if (!isEnabled()) {
        return;
    }
    increment("{operation}.count");
    addEvent(new DiagnosticEvent(
        "{OPERATION}_STARTED",
        details,
        null
    ));
}

public static void record{Operation}Timing(long durationMs) {
    if (!isEnabled()) {
        return;
    }
    timers.computeIfAbsent("{operation}.duration", k -> new TimingStats())
         .record(durationMs);
}
```

#### Error Recording
```java
public static void record{Operation}Failure(String reason, {Config} config) {
    if (!isEnabled()) {
        return;
    }
    
    increment("{operation}.failures");
    
    // Create error signature for grouping similar errors
    String errorSignature = "{OPERATION}_FAILURE|" + normalizeErrorMessage(reason);
    String formattedMessage = formatErrorMessage(reason, config);
    String recommendation = getRecommendationFor{Operation}Error(reason);
    
    // Update or create error stats
    errorStats.computeIfAbsent(
        errorSignature, 
        k -> new ErrorStats(formattedMessage, recommendation)
    ).recordOccurrence();
    
    // Also add to general event list
    addEvent(new DiagnosticEvent(
        "{OPERATION}_FAILURE",
        formattedMessage,
        recommendation
    ));
}

// Helper method to normalize error messages for grouping
private static String normalizeErrorMessage(String message) {
    if (message == null) {
        return "null";
    }
    
    // Remove variable data like timestamps, IDs, etc.
    return message
        .replaceAll("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}.*?\\s", "") // Remove ISO timestamps
        .replaceAll("\\b[0-9a-f]{8}\\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\\b[0-9a-f]{12}\\b", "<uuid>") // UUIDs
        .replaceAll("\\d+\\.\\d+\\.\\d+\\.\\d+", "<ip>") // IP addresses
        .replaceAll("\\d+", "<n>") // Any numbers
        .replaceAll("\\s+", " ") // Normalize whitespace
        .trim();
}

private static String getRecommendationFor{Operation}Error(String reason) {
    // Match common error patterns and provide specific recommendations
    if (reason.contains("connection")) {
        return "Check network connectivity to the service";
    } else if (reason.contains("timeout")) {
        return "Verify service response time or increase timeout settings";
    }
    // Default recommendation
    return "Contact system administrator if issue persists";
}
```

#### Status Reporting
```java
public static String getStatus() {
    if (!isEnabled()) {
        return "{Component} diagnostics is currently disabled. Enable it with {Component}Diagnostics.enable() to collect diagnostic information.";
    }
    
    StringBuilder status = new StringBuilder("{Component} Diagnostic Report\n");
    status.append("Generated: ").append(Instant.now()).append("\n");
    
    // Add metrics
    status.append("\nMetrics:\n");
    if (counters.isEmpty() && timers.isEmpty()) {
        status.append("No metrics recorded yet\n");
    } else {
        counters.forEach((key, value) ->
                status.append(String.format("%-30s: %d\n", key, value.sum())));
        timers.forEach((key, value) ->
                status.append(String.format("%-30s: avg=%.2fms min=%dms max=%dms\n", 
                                          key, 
                                          value.getAverageMs(),
                                          value.getMinMs(),
                                          value.getMaxMs())));
    }

    // Add error statistics with grouped occurrences
    status.append("\nError Summary:\n");
    if (errorStats.isEmpty()) {
        status.append("No errors recorded\n");
    } else {
        errorStats.values().forEach(error -> {
            status.append("\n[ERROR] ").append(error.getMessage());
            if (error.getOccurrences() > 1) {
                status.append(" (").append(error.getOccurrences()).append(" occurrences)");
            }
            status.append("\nFirst seen: ").append(error.getFirstSeen());
            if (error.getOccurrences() > 1) {
                status.append("\nLast seen: ").append(error.getLastSeen());
            }
            if (error.getRecommendation() != null) {
                status.append("\nRecommended Action: ").append(error.getRecommendation());
            }
            status.append("\n");
        });
    }
    
    // Add general events (non-error events)
    status.append("\nRecent Events (newest first):\n");
    synchronized (events) {
        if (events.isEmpty()) {
            status.append("No events recorded yet\n");
        } else {
            events.stream()
                  .filter(event -> !event.type.endsWith("_FAILURE"))
                  .forEach(event -> {
                      status.append("\n").append(event.toString());
                      if (event.recommendation != null) {
                          status.append("\nRecommended Action: ").append(event.recommendation);
                      }
                      status.append("\n");
                  });
        }
    }

    return status.toString();
}
```

#### Helper Methods
```java
private static void increment(String metric) {
    if (!isEnabled()) {
        return;
    }
    counters.computeIfAbsent(metric, k -> new LongAdder()).increment();
}

private static void increment(String metric, int value) {
    if (!isEnabled() || value == 0) {
        return;
    }
    counters.computeIfAbsent(metric, k -> new LongAdder()).add(value);
}

private static void addEvent(DiagnosticEvent event) {
    if (!isEnabled()) {
        return;
    }
    
    synchronized (events) {
        events.add(0, event); // Add new events at beginning
        if (events.size() > MAX_EVENTS) {
            events.remove(events.size() - 1); // Remove oldest when full
        }
    }
    logger.info(event.message);
}

public static void clearDiagnostics() {
    if (!isEnabled()) {
        return;
    }
    
    counters.clear();
    timers.clear();
    errorStats.clear();
    synchronized (events) {
        events.clear();
    }
    logger.info("{Component} diagnostics data cleared");
}
```

## Usage Example

### Application Code Integration
```java
// In application startup code
if (isDevelopmentEnvironment()) {
    VectorStoreDiagnostics.enable();
}

// In operation code
try {
    if (VectorStoreDiagnostics.isEnabled()) {
        VectorStoreDiagnostics.recordEmbeddingRequest();
        long startTime = System.currentTimeMillis();
        float[] embedding = embeddingService.generateEmbedding(params, text).block();
        long duration = System.currentTimeMillis() - startTime;
        VectorStoreDiagnostics.recordEmbeddingTiming(duration);
    }
    // Process embedding...
} catch (Exception e) {
    if (VectorStoreDiagnostics.isEnabled()) {
        VectorStoreDiagnostics.recordEmbeddingFailure(e.getMessage(), params);
    }
    throw e;
}
```

### Test Team Troubleshooting Example
```java
// Enable diagnostics before test
VectorStoreDiagnostics.enable();

// Run test that might have issues
List<Chart> searchResults = vectorService.findRelevantCharts("sales by region");

// Check for issues if results are unexpected
if (searchResults.isEmpty()) {
    // Get complete diagnostic report with timestamps, metrics and recommendations
    String diagnosticReport = VectorStoreDiagnostics.getStatus();
    System.out.println(diagnosticReport);
    
    // Take action based on recommendations in the report
    // Example output might indicate:
    // - Embedding service is unreachable
    // - Vector store is empty
    // - Query has no semantic matches in the database
}

// Disable diagnostics when finished to free memory
VectorStoreDiagnostics.disable();
```

## Best Practices

1. Error Management
   - Group similar errors by "error signature" with occurrence counts
   - Show first and last occurrence times for recurring issues
   - Normalize error messages to strip out variable data (timestamps, IDs, etc.)
   - Provide specific recommendations for each error type

2. Performance
   - Atomic operations for thread safety
   - Memory-efficient representation of errors (group duplicates)
   - Only collect diagnostics when explicitly enabled
   - Clear memory when disabled

3. Usability
   - Clear separation of errors from regular events in reports
   - Include occurrence counts for recurring issues
   - Actionable recommendations tied to error patterns
   - Easy enable/disable controls for testing sessions

4. Maintenance
   - Thread-safe operations throughout
   - Consistent formatting for readability
   - Complete cleanup on disable to free memory
   - Normalize error messages for better grouping

## Implementation Notes

1. Group similar errors by error signature to reduce noise while preserving occurrence information
2. Track first and last occurrences of each error type to help identify timing-related issues
3. Separate error summary from general events in status reports for better readability
4. Include timestamps for all events
5. Provide clear, actionable recommendations
6. Include configuration context in errors
7. Add data state information where relevant
8. Use thread-safe collections
9. Implement cleanup mechanism
10. Check isEnabled() before performing any operations
11. Enable/disable functionality to control memory usage
12. Properly initialize all collections to prevent NPEs

## When to Create a Diagnostic Utility

Create a dedicated diagnostic utility when a component:

1. Has complex configuration that impacts behavior
2. Interacts with external services that may fail
3. Contains state that influences operation outcomes
4. Is frequently used by test teams 
5. Generates errors that require specific domain knowledge to interpret

For example, create separate utilities for:
- Embedding services
- Vector stores
- Authentication systems
- Database connections
- File processing components
- API clients

Each component's diagnostic utility is designed to answer the question: "Why isn't this specific component working as expected?" without requiring log analysis or developer intervention.
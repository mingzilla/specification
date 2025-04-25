# Diagnostics Utility Library - API Documentation

This document provides a concise overview of the Diagnostics Utility Library API for integration into applications.

## Core Components

### DiagnosticsMetadata

Immutable record containing metadata for diagnostic events.

```java
public record DiagnosticsMetadata(String topic, String operation, String requestId) {
    public static DiagnosticsMetadata of(String topic, String operation, String requestId);
}
```

### DiagnosticsUtil

The main entry point for diagnostics operations.

```java
public class DiagnosticsUtil {
    // Request Management
    public static String generateRequestId();
    public static void enableTopic(String topic);
    public static void disableTopic(String topic);
    public static boolean isTopicEnabled(String topic);
    
    // Logging Methods
    public static void debug(DiagnosticsMetadata metadata, String stage, String message);
    public static void info(DiagnosticsMetadata metadata, String stage, String message);
    public static void info(DiagnosticsMetadata metadata, String stage, String message, Map<String, ? extends Object> data);
    public static void warn(DiagnosticsMetadata metadata, String stage, String message);
    public static void warn(DiagnosticsMetadata metadata, String stage, String message, Map<String, ? extends Object> data);
    public static void error(DiagnosticsMetadata metadata, String stage, String message, Throwable ex);
    public static void error(DiagnosticsMetadata metadata, String stage, String message, Throwable ex, Map<String, ? extends Object> data);
    
    // Diagnostic Summary Methods
    public static String getDiagnosticSummary(String topic);
    public static void clearDiagnostics(String topic);
    public static void clearAllDiagnostics();
    
    // Utility Methods
    public static String maskSensitiveUrl(String url);
}
```

### DiagnosticsReactiveUtil

Support for tracking diagnostic events in reactive streams.

```java
public class DiagnosticsReactiveUtil<T> {
    // Factory Methods
    public static <T> DiagnosticsReactiveUtil<T> chainMono(DiagnosticsMetadata metadata, Mono<T> mono, Map<String, ? extends Object> requestData);
    public static <T> DiagnosticsReactiveUtil<T> chainFlux(DiagnosticsMetadata metadata, Flux<T> flux, Map<String, ? extends Object> requestData);
    
    // Lifecycle Methods
    public DiagnosticsReactiveUtil<T> doOnSubscribe(Consumer<? super Subscription> onSubscribe);
    public DiagnosticsReactiveUtil<T> doOnSuccess(Consumer<? super T> onSuccess);
    public DiagnosticsReactiveUtil<T> doOnError(Consumer<Throwable> onError);
    public DiagnosticsReactiveUtil<T> doFinally(Consumer<SignalType> onFinally);
    
    // Terminal Operation
    public Mono<T> applyMono();
    public Flux<T> applyFlux();
    
    // Stage Constants
    public static class Stage {
        public static final String READY = "READY";
        public static final String SUBSCRIBE = "SUBSCRIBE";
        public static final String SUCCESS = "SUCCESS";
        public static final String ERROR = "ERROR";
        public static final String FINALLY = "FINALLY";
    }
}
```

## Usage Examples

### Basic Usage

```java
public void usage() {
    // Generate a request ID
    String requestId = DiagnosticsUtil.generateRequestId();
 
    // Enable diagnostics for a topic
    DiagnosticsUtil.enableTopic("VECTOR_DB");
 
    // Create metadata for the request
    DiagnosticsMetadata metadata = DiagnosticsMetadata.of("VECTOR_DB", "BULK_LOAD", requestId);
 
    // Log with context data
    Map<String, Object> params = Map.of(
            "vectorStoreConfig", config,
            "inputSize", inputs.size()
    );
    DiagnosticsUtil.info(metadata, "READY", "Starting bulk load", params);
 
    try {
       // Process request
       DiagnosticsUtil.info(metadata, "STARTED", "Processing started");
       // ... processing logic ...
       if (results.isEmpty()) {
          Map<String, Object> context = Map.of(
                  "filters", searchFilters,
                  "expectedResults", true
          );
          DiagnosticsUtil.warn(metadata, "NO_RESULTS", "Query returned no matching records", context);
       } else {
          DiagnosticsUtil.info(metadata, "SUCCEEDED", "Processing completed");
       }
    } catch (Exception e) {
       DiagnosticsUtil.error(metadata, "FAILED", "Processing failed", e);
       throw e;
    } finally {
       DiagnosticsUtil.info(metadata, "ENDED", "Request ended");
    }
 
    // View diagnostics
    String summary = DiagnosticsUtil.getDiagnosticSummary("VECTOR_DB");
    System.out.println(summary);
}
```

### Reactive Usage

```java
public Mono<Void> reactiveUsage() {
    // Create metadata for the request
    DiagnosticsMetadata metadata = DiagnosticsMetadata.of("DATA_FETCH", "USER_LOOKUP", requestId);

    // Add context data
    Map<String, Object> requestData = Map.of(
            "userId", userId,
            "requestTime", Instant.now()
    );

    // Create a reactive stream
    Mono<User> userMono = userRepository.findById(userId)
            .flatMap(user -> validateUser(user))
            .onErrorResume(e -> fallbackUser());

    // Instrument the Mono chain with diagnostics
    return DiagnosticsReactiveUtil.chainMono(metadata, userMono, requestData)
           .doOnSubscribe(s -> System.out.println("Subscribed"))
           .doOnSuccess(v -> System.out.println("Success"))
           .doOnError(e -> System.out.println("Error: " + e.getMessage()))
           .doFinally(signal -> System.out.println("Completed with signal: " + signal))
           .applyMono();
}
```

## Common Use Cases

1. **Configuration Validation**
    - Record configuration parameters at the start of operations
    - Validate and report issues with external service configurations
    - Track connection attempts to dependent services

2. **Error Tracking**
    - Correlate errors across distributed systems using request IDs
    - Capture detailed context at failure points
    - Provide actionable troubleshooting information

3. **Performance Monitoring**
    - Track operation durations across request lifecycles
    - Identify slow operations or unexpected delays
    - Correlate performance issues with configuration settings

## Diagnostic Summary Format

```
[Topic: VECTOR_DB]
[Operation: BULK_LOAD]
Request ID: req-123-456
Duration: 1500ms

[2024-01-20 10:15:30.123] INFO READY
  Message: Starting bulk load
  Context: {
    "vectorStoreConfig": {...},
    "inputSize": 100
  }

[2024-01-20 10:15:30.234] INFO STARTED
  Message: Request started

[2024-01-20 10:15:30.345] WARN NO_RESULTS
  Message: Query returned zero results
  Context: {
    "query": "embedding_id=123",
    "filters": {"status": "active"},
    "expectedResults": true
  }

[2024-01-20 10:15:31.456] ERROR FAILED
  Message: Failed to connect to embedding service
  Exception: java.net.ConnectException: Connection refused
  Context: {
    "url": "http://embedding-service:8080",
    "timeout": 5000
  }

[2024-01-20 10:15:31.623] INFO ENDED
  Message: Request ended
```

## Best Practices

1. Use consistent topic names across the application
2. Keep diagnostic data focused on external interactions and configuration
3. Include relevant context data for troubleshooting
4. Clean up old diagnostic data regularly with `clearDiagnostics()` or `clearAllDiagnostics()`
5. Use meaningful stage names for better readability
6. Include configuration data in the READY stage
7. Always log both success and failure outcomes
8. Use request IDs consistently throughout the request lifecycle
9. Use warning level for expected but unusual conditions (zero results, etc.)
10. Configure appropriate masking for sensitive data using `maskSensitiveUrl()`
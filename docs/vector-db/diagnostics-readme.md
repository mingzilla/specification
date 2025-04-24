# Diagnostics Utility Library

A lightweight, thread-safe diagnostics library for tracking and troubleshooting application operations, with a focus on configuration validation and error tracking. This library provides structured diagnostic events with metadata, context data, and proper error handling.

## Features

- Thread-safe implementation using ConcurrentHashMap
- Topic-based diagnostic event collection and filtering
- Support for reactive streams with DiagnosticsReactiveUtil
- Detailed event tracking with timing information
- Memory-efficient storage with automatic cleanup
- Request ID generation for correlation
- Configurable data masking for sensitive information

## Quick Start

```java
// Generate a request ID
String requestId = DiagnosticsUtil.generateRequestId();

// Enable diagnostics for a topic
DiagnosticsUtil.enableTopic("VECTOR_DB");

// Create metadata for the request
DiagnosticsMetadata metadata = DiagnosticsMetadata.of("VECTOR_DB", "BULK_LOAD", requestId);

// Log operation start with context data
Map<String, Object> params = Map.of("configParam", "value");
DiagnosticsUtil.info(metadata, "STARTED", "Operation started", params);

try {
    // Perform operation...
    DiagnosticsUtil.info(metadata, "COMPLETED", "Operation completed successfully");
} catch (Exception e) {
    DiagnosticsUtil.error(metadata, "FAILED", "Operation failed", e);
    throw e;
}

// Get diagnostic summary
String summary = DiagnosticsUtil.getDiagnosticSummary("VECTOR_DB");
System.out.println(summary);
```

## Documentation

The library includes comprehensive documentation to help you get started and understand the detailed behavior:

- [API Manual](diagnostics-api-manual.md): Method signatures, usage examples, and best practices
- [Behavior Specification](diagnostics-behaviour-spec.md): Technical details of component interactions and system behavior

## Core Components

### DiagnosticsUtil

The main entry point for diagnostics operations, providing methods to:

- Generate request IDs
- Enable/disable topics
- Log diagnostic events at different levels (INFO, WARN, ERROR)
- Retrieve diagnostic summaries
- Manage diagnostic data lifecycle

### DiagnosticsMetadata

Immutable record containing metadata for diagnostic events:

- topic: The diagnostic category
- operation: The specific operation being performed
- requestId: Unique identifier for correlating events

### DiagnosticsReactiveUtil

Support for tracking diagnostic events in reactive streams (Mono/Flux), with methods to:

- Chain diagnostics to reactive streams
- Track lifecycle events (subscribe, success, error, completion)
- Propagate context across asynchronous boundaries

## Related Documents
- [API Manual](diagnostics-api-manual.md)
- [Behavior Specification](diagnostics-behaviour-spec.md)

## License

[MIT License](LICENSE)
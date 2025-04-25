# Diagnostics Utility System Specification

## Problem Statement

Diagnosing issues in modern applications requires structured logging that can:

- Track configuration validation issues that cause failures
- Correlate events across distributed systems
- Provide actionable troubleshooting information
- Support reactive programming models

## Core Components

| Component                   | Structure                                                             | Primary Purpose                        | Key Features                                            |
|-----------------------------|-----------------------------------------------------------------------|----------------------------------------|---------------------------------------------------------|
| **DiagnosticsMetadata**     | `record(topic, operation, requestId)`                                 | Provides context for diagnostic events | Immutable, thread-safe, correlates related events       |
| **DiagnosticsUtil**         | Static utility class                                                  | Main entry point for diagnostics       | Thread-safe operations, topic management, log levels    |
| **DiagnosticEvent**         | Class with records list                                               | Contains all records for a request     | Memory-efficient storage, formatted event summary       |
| **DiagnosticEventRecord**   | `record(metadata, stage, timestamp, level, message, exception, data)` | Individual diagnostic event data       | Immutable data structure, context storage               |
| **DiagnosticsReactiveUtil** | Generic class with reactive streams                                   | Integrates with Project Reactor        | Stream lifecycle monitoring, proper resource management |

## Topic Management Operations

| Operation          | When Used                                                                                   | Behavior                                                                                                                  |
|--------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **enableTopic**    | • Application startup<br>• Feature activation<br>• Troubleshooting sessions                 | • Sets topic status to active<br>• Creates storage structures if needed<br>• Logs activation with INFO level              |
| **disableTopic**   | • Normal operation resumption<br>• Reducing memory usage<br>• End of troubleshooting        | • Sets topic status to inactive<br>• Clears all diagnostic events for the topic<br>• Logs deactivation with INFO level    |
| **isTopicEnabled** | • Before recording events (internal)<br>• UI status indicators<br>• Conditional diagnostics | • Checks current status without side effects<br>• Returns true only if explicitly enabled<br>• Thread-safe implementation |

## Diagnostic Event Levels

| Level     | When Used                                                                                       | Behavior                                                                                                                                      |
|-----------|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **INFO**  | • Normal operation steps<br>• Successful operations<br>• Configuration values                   | • Always logged to SLF4J<br>• Only stored in diagnostics if topic enabled<br>• No exception context                                           |
| **WARN**  | • Expected but unusual conditions<br>• Performance degradation<br>• Fallback behavior activated | • Always logged to SLF4J with WARN level<br>• Only stored in diagnostics if topic enabled<br>• No exception context                           |
| **ERROR** | • Operation failures<br>• Invalid configuration<br>• External service issues                    | • Always logged to SLF4J with ERROR level<br>• Only stored in diagnostics if topic enabled<br>• Includes exception stack trace when available |
| **DEBUG** | • Low-level details<br>• Developer troubleshooting                                              | • Only logged to SLF4J if level enabled<br>• Never stored in diagnostics events<br>• No memory impact                                         |

## Reactive Streams Integration

| Operation               | Implementation                                   | Purpose                                           |
|-------------------------|--------------------------------------------------|---------------------------------------------------|
| **chainMono**           | Factory method with static typing                | Creates a diagnostic wrapper for Mono streams     |
| **chainFlux**           | Factory method with static typing                | Creates a diagnostic wrapper for Flux streams     |
| **applyMono/applyFlux** | Terminal operation returning instrumented stream | Applies diagnostics at each lifecycle stage       |
| **Lifecycle Hooks**     | doOnSubscribe, doOnSuccess, doOnError, doFinally | Captures each stage of reactive stream processing |

## Key Diagnostic Operations

| Operation                 | Method Signature                       | Behavior                                                                                                                     |
|---------------------------|----------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| **Request ID Generation** | `generateRequestId()`                  | • Creates UUID for correlation<br>• Guaranteed thread-safe uniqueness<br>• Returns as String                                 |
| **Basic Logging**         | `info(metadata, stage, message)`       | • Logs to SLF4J with metadata context<br>• Stores in diagnostics if topic enabled<br>• Uses current timestamp                |
| **Contextual Logging**    | `info(metadata, stage, message, data)` | • Same as basic logging<br>• Also stores context Map data<br>• Map data is logged and retrievable later                      |
| **Error Logging**         | `error(metadata, stage, message, ex)`  | • Logs exception context to SLF4J<br>• Stores exception in diagnostic event<br>• Includes stack trace in diagnostics         |
| **Getting Summary**       | `getDiagnosticSummary(topic)`          | • Formats all events for a topic<br>• Includes timing, context data, exceptions<br>• Returns empty message if topic disabled |
| **Clearing Data**         | `clearDiagnostics(topic)`              | • Removes all events for a topic<br>• Retains topic enabled status<br>• Thread-safe operation                                |

## Memory Management

| Mechanism               | Implementation                                                  | Behavior                                         |
|-------------------------|-----------------------------------------------------------------|--------------------------------------------------|
| **Topic-Based Storage** | ConcurrentMap per topic                                         | Events only stored when topic explicitly enabled |
| **Conditional Storage** | Gate check before storage                                       | No memory impact for disabled topics             |
| **Event Clearing**      | On-demand and auto-clearing                                     | Clear on disable, explicit clear methods         |
| **Map Structure**       | `ConcurrentMap<String, ConcurrentMap<String, DiagnosticEvent>>` | Two-level map: topic → requestId → event         |

## Behavior in Concurrent Scenarios

| Scenario                                    | Initial State                      | Trigger Action                    | Behavior                                                  |
|---------------------------------------------|------------------------------------|-----------------------------------|-----------------------------------------------------------|
| **Multiple threads logging same request**   | Topic enabled, request in progress | Concurrent logging calls          | Thread-safe updates to same DiagnosticEvent, no data loss |
| **Multiple requests logged simultaneously** | Topic enabled, system under load   | Multiple requests with unique IDs | Separate DiagnosticEvent instances created per requestId  |
| **Topic enabled/disabled during operation** | Topic status changing              | Dynamic configuration change      | Safe state transitions, in-progress operation completes   |
| **Reactive stream cancelation**             | Stream in progress                 | Subscription canceled             | doFinally handler executes, proper state recording        |
| **Thread pool execution**                   | Bounded elastic scheduler          | Task submission                   | Context preserved across thread boundaries                |

## Diagnostic Output Content

The diagnostic output includes:

- Request metadata (topic, operation, requestId)
- Duration calculation from first to last event
- Chronological list of all events with:
    - Timestamp in ISO-8601 format
    - Event level (INFO, WARN, ERROR)
    - Processing stage label
    - Message content
    - Exception details when present
    - Context data map contents
- Section separators for readability

## URL Sanitization

For security, the system automatically:

- Detects URL formats containing credentials
- Masks user:password sections in URLs
- Substitutes with `*****@` placeholder
- Applied in context data and message content
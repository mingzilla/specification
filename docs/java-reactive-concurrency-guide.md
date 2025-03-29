# Java Concurrency & Project Reactor: A Comprehensive Guide

## Java Concurrent Framework vs Project Reactor Overview

```
+--------------------------------------+    +------------------------------------+
|        java.util.concurrent          |    |         Project Reactor            |
+--------------------------------------+    +------------------------------------+
|                                      |    |                                    |
|  +-------------+  +---------------+  |    |  +-------------+  +-------------+  |
|  |  Executors  |  |ExecutorService|  |    |  | Schedulers  |  | Scheduler   |  |
|  |-------------|  |---------------|  |    |  |-------------|  |-------------|  |
|  | Factory     |  | Interface     |  |    |  | Factory     |  | Interface   |  |
|  | methods to  |  | for thread    |  |    |  | methods for |  | for async   |  |
|  | create      |  | pool mgmt     |  |    |  | scheduler   |  | execution   |  |
|  | thread pools|  |               |  |    |  | instances   |  | in streams  |  |
|  +-------------+  +---------------+  |    |  +-------------+  +-------------+  |
|                                      |    |                                    |
+--------------------------------------+    +------------------------------------+
                  |                                          ^
                  |                                          |
                  +------------------------------------------+
                            Built on top of / Extends
```

## Java Concurrency vs Project Reactor: Method Comparison

| Category                | Java Executors Method           | Project Reactor Schedulers Method | Purpose                    | Thread Lifecycle                                                                               | Best For                                 |
| ----------------------- | ------------------------------- | --------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Fixed-size Pool**     | `newFixedThreadPool(n)`         | `parallel()`                      | Limited thread pool        | Java: Permanent until shutdown<br>Reactor: Permanent                                           | CPU-bound tasks, parallel processing     |
| **Elastic Pool**        | `newCachedThreadPool()`         | `boundedElastic()`                | Scalable thread pool       | Java: Unlimited growth, 60s idle timeout<br>Reactor: Bounded growth (CPU×10), 60s idle timeout | I/O operations, blocking calls           |
| **Single Thread**       | `newSingleThreadExecutor()`     | `single()`                        | One worker thread          | Java: Permanent until shutdown<br>Reactor: Permanent                                           | Sequential execution, ordered operations |
| **Immediate Execution** | N/A (would be direct execution) | `immediate()`                     | No thread switch           | N/A (current thread)                                                                           | Testing, avoiding context switches       |
| **Timer**               | `newScheduledThreadPool(n)`     | `newParallel("timer", n)`         | Delayed/periodic execution | Java: Permanent until shutdown<br>Reactor: Permanent                                           | Scheduling tasks, timeouts               |
| **Custom**              | `new ThreadPoolExecutor(...)`   | `fromExecutorService(exec)`       | Custom configuration       | Depends on configuration                                                                       | Special threading requirements           |

## Usage Examples

### Java Executors
```java
// Fixed thread pool
ExecutorService fixedPool = Executors.newFixedThreadPool(4);
fixedPool.submit(() -> processCpuIntensiveTask());

// Cached thread pool
ExecutorService cachedPool = Executors.newCachedThreadPool();
cachedPool.submit(() -> handleRequest());

// Single thread executor
ExecutorService singleThread = Executors.newSingleThreadExecutor();
singleThread.submit(() -> processInOrder());

// Always close executors when done
fixedPool.shutdown();
```

### Project Reactor Schedulers
```java
// Parallel scheduler
Flux.range(1, 1000)
    .publishOn(Schedulers.parallel())
    .map(i -> performCalculation(i))
    .subscribe();

// BoundedElastic scheduler
Mono.fromCallable(() -> blockingDatabaseCall())
    .subscribeOn(Schedulers.boundedElastic())
    .subscribe(data -> process(data));

// Single scheduler
Flux.range(1, 100)
    .publishOn(Schedulers.single())
    .map(i -> processSequentially(i))
    .subscribe();
```

## Terminologies Comparison

Here's a side-by-side comparison of Java Reactor and JavaScript RxJS equivalents:

| Java (Project Reactor)                     | JavaScript (RxJS)                  | Purpose                                     |
| ------------------------------------------ | ---------------------------------- | ------------------------------------------- |
| `Mono`                                     | `Observable` (single value)        | Container for 0-1 async values              |
| `Flux`                                     | `Observable` (multiple values)     | Container for 0-n async values              |
| `Mono.fromCallable()`                      | `from(new Promise())` or `defer()` | Create observable from function call        |
| `subscribeOn(Schedulers.boundedElastic())` | `observeOn(asyncScheduler)`        | Control which thread pool executes the work |
| `subscribe(data -> process(data))`         | `subscribe(data => process(data))` | Terminal operation to start the chain       |
| `Schedulers.boundedElastic()`              | `asyncScheduler`                   | Thread pool for I/O operations              |
| `Schedulers.parallel()`                    | `queueScheduler`                   | Thread pool for CPU-bound work              |

Complete example conversion:

```java
// Java - Project Reactor
Mono.fromCallable(() -> blockingDatabaseCall())
    .subscribeOn(Schedulers.boundedElastic())
    .subscribe(data -> process(data));
```

```javascript
// JavaScript (RxJS)
import { defer, from, observeOn, asyncScheduler } from 'rxjs';
defer(() => from(blockingDatabaseCall())) // from: Similar to `Observable.from()`
    .pipe(observeOn(asyncScheduler))
    .subscribe(data => process(data));
```

Here's the RxJS comparison with the WHAT values filled in:

| Component         | RxJS Code                                                       | What it is                                                                           |
| ----------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Source creator    | `defer(() => from(blockingDatabaseCall()))`                     | Creates a lazy observable that runs `blockingDatabaseCall()` only when subscribed to |
| Operator          | `from(fetch('/api/data')).subscribe(resp => console.log(resp))` | from - async - converts promises into observables                                    |
| Operator          | `from([1, 2, 3]).subscribe(num => console.log(num))`            | from - sync - converts arrays into Observables that emit each array element          |
| Operator          | `Observable.pipe(observeOn(asyncScheduler))`                    | Pipe method to apply operators to the observable                                     |
| Thread management | `observeOn(asyncScheduler)`                                     | Controls which scheduler/thread processes emissions                                  |
| Thread pool       | `asyncScheduler`                                                | RxJS's asynchronous scheduler, an optimised `setTimeout()`                           |
| Consumer          | `subscribe(data => process(data))`                              | Terminal operation that starts the observable chain                                  |


## Key Differences

1. **Resource Management**: 
   - Executors require explicit shutdown
   - Schedulers handle cleanup automatically when unused

2. **Bounded Resources**:
   - CachedThreadPool can grow unbounded (risk of resource exhaustion)
   - boundedElastic has strict upper limits on thread count

3. **Reactive Integration**:
   - Schedulers preserve reactive context and backpressure
   - Executors have no built-in backpressure handling

4. **Execution Model**:
   - Executors focus on executing discrete tasks
   - Schedulers focus on when/where to process reactive streams

## Project Reactor Operators: `subscribeOn`, `publishOn`, and `subscribe`

| Operator                   | Primary Purpose                                  | Thread Execution                       | Multiple Calls                          | Scheduler Integration                                                              |
| -------------------------- | ------------------------------------------------ | -------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------- |
| **subscribeOn(Scheduler)** | Controls subscription and source emission thread | Affects upstream operators and source  | Only first call has effect              | `Mono.fromCallable(() -> blockingCall()).subscribeOn(Schedulers.boundedElastic())` |
| **publishOn(Scheduler)**   | Controls downstream operator execution thread    | Affects only operators after publishOn | Each call changes thread for downstream | `Flux.range(1, 10).publishOn(Schedulers.parallel()).map(...)`                      |
| **subscribe()**            | Initiates reactive chain execution               | Executes on calling thread by default  | Terminal operation - starts chain       | `flux.subscribe(data -> {}, error -> {}, () -> {})`                                |

```
// subscribeOn affects entire chain upstream
+-----------------------------------------------------+
|                                                     |
| [subscribeOn(boundedElastic)] --> [map] --> [filter]|
|       ^                                             |
|       |                                             |
| Everything upstream runs on boundedElastic thread   |
+-----------------------------------------------------+

// publishOn affects only operators downstream
+-----------------------------------------------------+
|                                                     |
| [map] --> [publishOn(parallel)] --> [filter]        |
|                   |                    |            |
|                   v                    v            |
|           Only downstream ops run on parallel thread|
+-----------------------------------------------------+
```

## Common Scheduler Integration Patterns

| Pattern                   | Code Example                                                                                                                                                                        | Description                                                    | Best For                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------- |
| **Blocking Operations**   | `Mono.fromCallable(() -> blockingDbCall())`<br>`.subscribeOn(Schedulers.boundedElastic())`                                                                                          | Moves blocking operation to boundedElastic thread              | Database calls, file I/O, external API calls |
| **Parallel Processing**   | `Flux.range(1, 1000)`<br>`.parallel()`<br>`.runOn(Schedulers.parallel())`<br>`.map(i -> compute(i))`<br>`.sequential()`                                                             | Splits work across parallel threads                            | CPU-intensive calculations                   |
| **UI Thread Management**  | `uiEventFlux`<br>`.publishOn(Schedulers.single())`<br>`.map(this::processEvent)`<br>`.publishOn(Schedulers.fromExecutor(uiExecutor))`                                               | Processes on background thread, publishes results on UI thread | Desktop/mobile applications                  |
| **Mixed Threading Model** | `Flux.range(1, 100)`<br>`.publishOn(Schedulers.parallel())`<br>`.map(this::heavyComputation)`<br>`.publishOn(Schedulers.boundedElastic())`<br>`.flatMap(id -> externalApiCall(id))` | Uses appropriate scheduler for each operation type             | Complex processing pipelines                 |

## Parallel Execution
If you need to execute parallel database calls and combine their results. Here's how to do this with Project Reactor:

```java
// Define your two blocking database calls
Mono<DataA> callA = Mono.fromCallable(() -> blockingDatabaseCallA())
    .subscribeOn(Schedulers.boundedElastic());

Mono<DataB> callB = Mono.fromCallable(() -> blockingDatabaseCallB())
    .subscribeOn(Schedulers.boundedElastic());

// Combine both results using zip
Mono<Tuple2<DataA, DataB>> combined = Mono.zip(callA, callB);

// Process the combined results
Flux<Result> results = combined.flatMapMany(tuple -> {
    DataA resultA = tuple.getT1();
    DataB resultB = tuple.getT2();
    return process(resultA, resultB);
});

// Subscribe to start the flow
results.subscribe(
    result -> System.out.println("Processed: " + result),
    error -> error.printStackTrace(),
    () -> System.out.println("Processing complete")
);
```

Key points:
- Each database call gets its own `subscribeOn(Schedulers.boundedElastic())`, allowing them to run on separate threads
- `Mono.zip()` waits for both operations to complete before continuing
- The results are accessible as a tuple with `getT1()` and `getT2()`
- For more than two operations, you can use `Mono.zip(mono1, mono2, mono3, ...)` or `Flux.zip()`

The operations will execute in parallel, potentially improving performance compared to sequential execution.

## Parallel Execution Approaches Comparison

| Aspect                        | Approach 1: `parallel()` with `Schedulers.parallel()`                                               | Approach 2: Multiple `Mono`s with `Schedulers.boundedElastic()`                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Best for**                  | CPU-bound operations (computation)                                                                  | I/O-bound operations (waiting)                                                          |
| **Use cases**                 | • Pure computational tasks<br>• Math operations<br>• Data transformations<br>• In-memory processing | • Database calls<br>• Network requests<br>• File operations<br>• External service calls |
| **Scheduler characteristics** | • Fixed-size pool based on CPU cores<br>• Optimized for computation                                 | • Dynamically sized, bounded pool<br>• Intelligent queuing with backpressure            |
| **Execution model**           | • Splits work across threads<br>• True parallel computation                                         | • Each task runs independently<br>• Concurrent, not necessarily parallel                |
| **Resource usage**            | • Higher CPU utilization<br>• Lower thread count                                                    | • Lower CPU utilization<br>• Higher thread count (but controlled)                       |
| **Code pattern**              | `Flux.range().parallel().runOn().map().sequential()`                                                | `Mono.zip(taskA, taskB).flatMap(results -> process(results))`                           |
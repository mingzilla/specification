package io.github.mingzilla.diagnostics;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.panintelligence.vector.model.EmbeddingParams;

/**
 * A diagnostic utility that provides real-time monitoring, error tracking,
 * and actionable recommendations for the vector store component. This
 * utility serves as a single source of truth for troubleshooting specific
 * system components without requiring log file analysis.
 * 
 * <p>
 * Example usage:
 * </p>
 * 
 * <pre>{@code
 * // Enable diagnostics before operations
 * VectorStoreDiagnostics.enable();
 * 
 * // Get detailed status including metrics, errors, and recommendations
 * String diagnosticReport = VectorStoreDiagnostics.getStatus();
 * 
 * // Clear diagnostic data when needed
 * VectorStoreDiagnostics.clearDiagnostics();
 * 
 * // Disable diagnostics when finished
 * VectorStoreDiagnostics.disable();
 * }</pre>
 * 
 * <p>
 * The diagnostic utility provides:
 * </p>
 * <ul>
 * <li>Real-time operation metrics and timing statistics</li>
 * <li>Error tracking with occurrence counts and timestamps</li>
 * <li>Actionable recommendations for common error conditions</li>
 * <li>Configuration state tracking</li>
 * <li>Memory-efficient error grouping</li>
 * </ul>
 * 
 * <p>
 * All diagnostic operations are thread-safe and only collect data when
 * explicitly enabled to minimize memory impact during normal operation.
 * </p>
 */
public class VectorStoreDiagnostics {
    private static final Logger logger = LoggerFactory.getLogger(VectorStoreDiagnostics.class);
    private static final int MAX_EVENTS = 100;
    private static final ConcurrentHashMap<String, LongAdder> counters = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, TimingStats> timers = new ConcurrentHashMap<>();
    private static final List<DiagnosticEvent> events = new ArrayList<>();
    private static final Map<String, ErrorStats> errorStats = new ConcurrentHashMap<>();
    private static final AtomicBoolean enabled = new AtomicBoolean(false);

    private VectorStoreDiagnostics() {
        // Prevent instantiation
    }

    public static void enable() {
        if (enabled.compareAndSet(false, true)) {
            logger.info("Vector store diagnostics enabled");
        }
    }

    public static void disable() {
        if (enabled.compareAndSet(true, false)) {
            clearDiagnostics();
            logger.info("Vector store diagnostics disabled");
        }
    }

    public static boolean isEnabled() {
        return enabled.get();
    }

    public static void recordEmbeddingRequest() {
        if (!isEnabled())
            return;
        increment("embedding.requests");
    }

    public static void recordEmbeddingFailure(String reason, EmbeddingParams params) {
        if (!isEnabled())
            return;
        increment("embedding.failures");

        String errorSignature = "EMBEDDING_FAILURE|" + normalizeErrorMessage(reason);
        String formattedMessage = String.format("Embedding failure: %s. Model: %s, URL: %s",
                reason, params.model(), params.url());
        String recommendation = String.format("Check if:\n" +
                "1. Embedding service is running at %s\n" +
                "2. Model '%s' is properly loaded\n" +
                "3. Network connectivity is available",
                params.url(), params.model());

        recordError(errorSignature, formattedMessage, recommendation);
    }

    public static void recordEmbeddingConfiguration(EmbeddingParams params) {
        if (!isEnabled())
            return;
        addEvent(new DiagnosticEvent(
                "CONFIGURATION",
                String.format("Embedding configuration - Model: %s, URL: %s",
                        params.model(), params.url()),
                null));
    }

    public static void recordVectorStoreStats(int totalVectors) {
        if (!isEnabled())
            return;
        increment("vectorstore.records", totalVectors);
        addEvent(new DiagnosticEvent(
                "VECTOR_STORE_STATUS",
                String.format("Vector store contains %d vectors", totalVectors),
                totalVectors == 0 ? "No vectors found. Ensure data has been properly indexed." : null));
    }

    public static void recordVectorStoreInsert() {
        if (!isEnabled())
            return;
        increment("vectorstore.inserts");
    }

    public static void recordSearchRequest() {
        if (!isEnabled())
            return;
        increment("vectorstore.searches");
    }

    public static void recordOperationFailure(String operation, String reason) {
        if (!isEnabled())
            return;
        increment("vectorstore.failures");

        String errorSignature = operation.toUpperCase() + "_FAILURE|" + normalizeErrorMessage(reason);
        String formattedMessage = String.format("Vector store %s operation failed: %s", operation, reason);
        String recommendation = getRecommendationForOperation(operation);

        recordError(errorSignature, formattedMessage, recommendation);
    }

    public static void recordEmbeddingTiming(long durationMs) {
        if (!isEnabled())
            return;
        timers.computeIfAbsent("embedding.duration", k -> new TimingStats())
                .record(durationMs);
    }

    public static String getStatus() {
        if (!isEnabled()) {
            return "Vector store diagnostics is currently disabled. Enable it with VectorStoreDiagnostics.enable() to collect diagnostic information.";
        }

        StringBuilder status = new StringBuilder("Vector Store Diagnostic Report\n");
        status.append("Generated: ").append(Instant.now()).append("\n");

        // Add metrics
        status.append("\nMetrics:\n");
        if (counters.isEmpty() && timers.isEmpty()) {
            status.append("No metrics recorded yet\n");
        } else {
            counters.forEach((key, value) -> status.append(String.format("%-30s: %d\n", key, value.sum())));
            timers.forEach((key, value) -> status.append(String.format("%-30s: avg=%.2fms min=%dms max=%dms\n",
                    key,
                    value.getAverageMs(),
                    value.getMinMs(),
                    value.getMaxMs())));
        }

        // Add error statistics
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

        // Add recent events
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

    public static void clearDiagnostics() {
        counters.clear();
        timers.clear();
        errorStats.clear();
        synchronized (events) {
            events.clear();
        }
        logger.info("Vector store diagnostics data cleared");
    }

    private static void increment(String metric) {
        if (!isEnabled())
            return;
        counters.computeIfAbsent(metric, k -> new LongAdder()).increment();
    }

    private static void increment(String metric, int value) {
        if (!isEnabled() || value == 0)
            return;
        counters.computeIfAbsent(metric, k -> new LongAdder()).add(value);
    }

    private static void addEvent(DiagnosticEvent event) {
        if (!isEnabled())
            return;

        synchronized (events) {
            events.add(0, event);
            if (events.size() > MAX_EVENTS) {
                events.remove(events.size() - 1);
            }
        }
        logger.info(event.message);
    }

    private static void recordError(String errorSignature, String message, String recommendation) {
        errorStats.computeIfAbsent(
                errorSignature,
                k -> new ErrorStats(message, recommendation)).recordOccurrence();

        addEvent(new DiagnosticEvent("ERROR", message, recommendation));
    }

    private static String normalizeErrorMessage(String message) {
        if (message == null)
            return "null";

        return message
                .replaceAll("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}.*?\\s", "")
                .replaceAll("\\b[0-9a-f]{8}\\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\\b[0-9a-f]{12}\\b", "<uuid>")
                .replaceAll("\\d+\\.\\d+\\.\\d+\\.\\d+", "<ip>")
                .replaceAll("\\d+", "<n>")
                .replaceAll("\\s+", " ")
                .trim();
    }

    private static String getRecommendationForOperation(String operation) {
        return switch (operation.toLowerCase()) {
            case "search" -> "1. Check if vector store contains data\n" +
                    "2. Verify search parameters\n" +
                    "3. Check if index is corrupted";
            case "insert" -> "1. Verify input data format\n" +
                    "2. Check available disk space\n" +
                    "3. Ensure write permissions";
            case "initialization" -> "1. Check if the vector store directory is accessible\n" +
                    "2. Verify system has sufficient memory\n" +
                    "3. Ensure no other process is locking the index";
            default -> "Contact system administrator if issue persists";
        };
    }

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

    private static class ErrorStats {
        private final AtomicInteger occurrences = new AtomicInteger(0);
        private final Instant firstSeen;
        private volatile Instant lastSeen;
        private final String message;
        private final String recommendation;

        ErrorStats(String message, String recommendation) {
            this.message = message;
            this.recommendation = recommendation;
            this.firstSeen = Instant.now();
            this.lastSeen = firstSeen;
        }

        void recordOccurrence() {
            occurrences.incrementAndGet();
            lastSeen = Instant.now();
        }

        int getOccurrences() {
            return occurrences.get();
        }

        Instant getFirstSeen() {
            return firstSeen;
        }

        Instant getLastSeen() {
            return lastSeen;
        }

        String getMessage() {
            return message;
        }

        String getRecommendation() {
            return recommendation;
        }
    }

    private static class TimingStats {
        private final LongAdder count = new LongAdder();
        private final LongAdder totalTime = new LongAdder();
        private final AtomicLong minTime = new AtomicLong(Long.MAX_VALUE);
        private final AtomicLong maxTime = new AtomicLong(0);

        void record(long durationMs) {
            count.increment();
            totalTime.add(durationMs);

            // Update min time
            long currentMin = minTime.get();
            while (durationMs < currentMin) {
                if (minTime.compareAndSet(currentMin, durationMs))
                    break;
                currentMin = minTime.get();
            }

            // Update max time
            long currentMax = maxTime.get();
            while (durationMs > currentMax) {
                if (maxTime.compareAndSet(currentMax, durationMs))
                    break;
                currentMax = maxTime.get();
            }
        }

        double getAverageMs() {
            long currentCount = count.sum();
            return currentCount > 0 ? (double) totalTime.sum() / currentCount : 0.0;
        }

        long getMinMs() {
            return minTime.get() == Long.MAX_VALUE ? 0 : minTime.get();
        }

        long getMaxMs() {
            return maxTime.get();
        }
    }
}
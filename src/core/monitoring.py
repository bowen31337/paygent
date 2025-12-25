"""
Performance monitoring and execution time tracking for Paygent.

Provides comprehensive performance metrics collection and monitoring
for agent execution, API endpoints, and system operations.
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Represents a single metric value with timestamp."""
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Statistics for a set of measurements."""
    count: int = 0
    min_val: float = float('inf')
    max_val: float = float('-inf')
    sum_val: float = 0.0
    values: list[float] = field(default_factory=list)

    def add_value(self, value: float) -> None:
        """Add a new value to the statistics."""
        self.count += 1
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.sum_val += value
        self.values.append(value)

    def get_average(self) -> float:
        """Get the average value."""
        return self.sum_val / self.count if self.count > 0 else 0.0

    def get_median(self) -> float:
        """Get the median value."""
        if not self.values:
            return 0.0
        return statistics.median(self.values)

    def get_p95(self) -> float:
        """Get the 95th percentile."""
        if len(self.values) < 2:
            return self.values[0] if self.values else 0.0
        return statistics.quantiles(self.values, n=100)[94]

    def get_p99(self) -> float:
        """Get the 99th percentile."""
        if len(self.values) < 2:
            return self.values[0] if self.values else 0.0
        return statistics.quantiles(self.values, n=100)[98]


class PerformanceRegistry:
    """Registry for tracking performance metrics."""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._metrics: dict[str, list[MetricValue]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._labels: dict[str, dict[str, str]] = {}

    def counter(self, name: str, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] += 1
        self._labels[key] = labels or {}

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._labels[key] = labels or {}

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram metric value."""
        key = self._make_key(name, labels)
        self._histograms[key].add_value(value)
        self._labels[key] = labels or {}

    def timer(self, name: str, duration_ms: float, labels: dict[str, str] | None = None) -> None:
        """Record a timing metric."""
        key = self._make_key(name, labels)
        self._timers[key].append(duration_ms)
        # Keep only recent timers to prevent memory growth
        if len(self._timers[key]) > self.max_history:
            self._timers[key] = self._timers[key][-self.max_history:]
        self._labels[key] = labels or {}

    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        """Create a unique key for the metric."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self._counters[key]

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, labels: dict[str, str] | None = None) -> PerformanceStats:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        return self._histograms[key]

    def get_timer_stats(self, name: str, labels: dict[str, str] | None = None) -> PerformanceStats:
        """Get timer statistics."""
        key = self._make_key(name, labels)
        stats = PerformanceStats()
        if key in self._timers:
            for value in self._timers[key]:
                stats.add_value(value)
        return stats

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics in a structured format."""
        metrics = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
            "timers": {},
            "labels": dict(self._labels),
        }

        for name, stats in self._histograms.items():
            metrics["histograms"][name] = {
                "count": stats.count,
                "min": stats.min_val if stats.count > 0 else 0,
                "max": stats.max_val if stats.count > 0 else 0,
                "average": stats.get_average(),
                "median": stats.get_median(),
                "p95": stats.get_p95(),
                "p99": stats.get_p99(),
            }

        for name, timer_values in self._timers.items():
            stats = PerformanceStats()
            for value in timer_values:
                stats.add_value(value)
            metrics["timers"][name] = {
                "count": stats.count,
                "min": stats.min_val if stats.count > 0 else 0,
                "max": stats.max_val if stats.count > 0 else 0,
                "average": stats.get_average(),
                "median": stats.get_median(),
                "p95": stats.get_p95(),
                "p99": stats.get_p99(),
            }

        return metrics

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._labels.clear()


class Timer:
    """Context manager for timing operations."""

    def __init__(self, registry: PerformanceRegistry, name: str, labels: dict[str, str] | None = None):
        self.registry = registry
        self.name = name
        self.labels = labels
        self.start_time: float | None = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.perf_counter() - self.start_time) * 1000  # Convert to milliseconds
            self.registry.timer(self.name, duration, self.labels)


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(self, registry: PerformanceRegistry | None = None):
        self.registry = registry or PerformanceRegistry()
        self._running = False
        self._monitor_task: asyncio.Task | None = None

    def start_monitoring(self) -> None:
        """Start background performance monitoring."""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background performance monitoring."""
        if self._running:
            self._running = False
            if self._monitor_task:
                self._monitor_task.cancel()
            logger.info("Performance monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(30)  # Wait before retry

    async def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        import psutil

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.registry.gauge("system.cpu.percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.registry.gauge("system.memory.percent", memory.percent)
            self.registry.gauge("system.memory.used_gb", memory.used / (1024**3))
            self.registry.gauge("system.memory.available_gb", memory.available / (1024**3))

            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            self.registry.gauge("process.memory.rss_gb", process_memory.rss / (1024**3))
            self.registry.gauge("process.memory.vms_gb", process_memory.vms / (1024**3))
            self.registry.gauge("process.cpu.percent", process.cpu_percent())

            # Network metrics (if available)
            try:
                net_io = psutil.net_io_counters()
                self.registry.gauge("system.network.bytes_sent", net_io.bytes_sent)
                self.registry.gauge("system.network.bytes_recv", net_io.bytes_recv)
            except Exception:
                pass  # Network stats not available

        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def record_api_call(self, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
        """Record an API call metric."""
        labels = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
        }

        # Increment counter
        self.registry.counter("api.calls.total", labels)

        # Record timing
        self.registry.timer("api.calls.duration", duration_ms, labels)

        # Record success/failure counters
        if 200 <= status_code < 400:
            self.registry.counter("api.calls.success", labels)
        else:
            self.registry.counter("api.calls.error", labels)

    def record_agent_execution(self, session_id: str, command: str, duration_ms: float, success: bool) -> None:
        """Record an agent execution metric."""
        labels = {
            "session_id": session_id,
            "command_type": self._classify_command(command),
        }

        # Increment counter
        self.registry.counter("agent.executions.total", labels)
        if success:
            self.registry.counter("agent.executions.success", labels)
        else:
            self.registry.counter("agent.executions.failed", labels)

        # Record timing
        self.registry.timer("agent.executions.duration", duration_ms, labels)

    def record_payment_operation(self, service: str, operation: str, duration_ms: float, success: bool) -> None:
        """Record a payment operation metric."""
        labels = {
            "service": service,
            "operation": operation,
        }

        # Increment counter
        self.registry.counter("payments.operations.total", labels)
        if success:
            self.registry.counter("payments.operations.success", labels)
        else:
            self.registry.counter("payments.operations.failed", labels)

        # Record timing
        self.registry.timer("payments.operations.duration", duration_ms, labels)

    def record_cache_operation(self, operation: str, cache_type: str, hit: bool, duration_ms: float) -> None:
        """Record a cache operation metric."""
        labels = {
            "operation": operation,
            "cache_type": cache_type,
        }

        # Increment counter
        self.registry.counter("cache.operations.total", labels)
        if hit:
            self.registry.counter("cache.operations.hit", labels)
        else:
            self.registry.counter("cache.operations.miss", labels)

        # Record timing
        self.registry.timer("cache.operations.duration", duration_ms, labels)

    def _classify_command(self, command: str) -> str:
        """Classify a command by type."""
        command_lower = command.lower()
        if any(word in command_lower for word in ["pay", "payment", "transfer"]):
            return "payment"
        elif any(word in command_lower for word in ["balance", "wallet"]):
            return "balance"
        elif any(word in command_lower for word in ["swap", "trade", "exchange"]):
            return "trade"
        elif any(word in command_lower for word in ["service", "discover", "find"]):
            return "discovery"
        else:
            return "other"

    def get_performance_report(self) -> dict[str, Any]:
        """Generate a comprehensive performance report."""
        metrics = self.registry.get_all_metrics()

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self._generate_summary(metrics),
            "api_performance": self._analyze_api_performance(metrics),
            "agent_performance": self._analyze_agent_performance(metrics),
            "cache_performance": self._analyze_cache_performance(metrics),
            "system_health": self._analyze_system_health(metrics),
        }

        return report

    def _generate_summary(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Generate performance summary."""
        total_api_calls = sum(v for k, v in metrics["counters"].items() if "api.calls.total" in k)
        total_agent_executions = sum(v for k, v in metrics["counters"].items() if "agent.executions.total" in k)
        total_payments = sum(v for k, v in metrics["counters"].items() if "payments.operations.total" in k)

        return {
            "total_api_calls": total_api_calls,
            "total_agent_executions": total_agent_executions,
            "total_payments": total_payments,
            "uptime_minutes": self._calculate_uptime(),
        }

    def _analyze_api_performance(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Analyze API performance metrics."""
        api_timings = {}

        for name, stats in metrics["timers"].items():
            if name.startswith("api.calls.duration"):
                api_timings[name] = stats

        return {
            "avg_response_time_ms": self._calculate_avg_response_time(api_timings),
            "p95_response_time_ms": self._calculate_p95_response_time(api_timings),
            "error_rate_percent": self._calculate_error_rate(metrics),
            "requests_per_minute": self._calculate_rpm(metrics),
        }

    def _analyze_agent_performance(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Analyze agent performance metrics."""
        agent_timings = {}

        for name, stats in metrics["timers"].items():
            if name.startswith("agent.executions.duration"):
                agent_timings[name] = stats

        return {
            "avg_execution_time_ms": self._calculate_avg_execution_time(agent_timings),
            "success_rate_percent": self._calculate_success_rate(metrics, "agent.executions"),
            "commands_by_type": self._get_commands_by_type(metrics),
        }

    def _analyze_cache_performance(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Analyze cache performance metrics."""
        cache_hits = sum(v for k, v in metrics["counters"].items() if "cache.operations.hit" in k)
        cache_misses = sum(v for k, v in metrics["counters"].items() if "cache.operations.miss" in k)
        total_cache_ops = cache_hits + cache_misses

        hit_rate = (cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0

        return {
            "hit_rate_percent": round(hit_rate, 2),
            "total_operations": total_cache_ops,
            "hits": cache_hits,
            "misses": cache_misses,
        }

    def _analyze_system_health(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Analyze system health metrics."""
        return {
            "cpu_usage_percent": metrics["gauges"].get("system.cpu.percent", 0),
            "memory_usage_percent": metrics["gauges"].get("system.memory.percent", 0),
            "process_memory_gb": metrics["gauges"].get("process.memory.rss_gb", 0),
        }

    def _calculate_uptime(self) -> float:
        """Calculate system uptime in minutes."""
        # This is a simplified calculation
        # In production, you'd track start time
        return 0.0

    def _calculate_avg_response_time(self, timings: dict[str, dict]) -> float:
        """Calculate average API response time."""
        if not timings:
            return 0.0

        total_time = sum(stats["average"] * stats["count"] for stats in timings.values())
        total_count = sum(stats["count"] for stats in timings.values())

        return total_time / total_count if total_count > 0 else 0.0

    def _calculate_p95_response_time(self, timings: dict[str, dict]) -> float:
        """Calculate 95th percentile response time."""
        if not timings:
            return 0.0

        all_values = []
        for stats in timings.values():
            # Use individual values if available, otherwise use samples based on count
            if "values" in stats:
                all_values.extend(stats["values"])
            else:
                # If no individual values, approximate using count and average
                # This is a simplification for when we don't have detailed timing data
                pass

        if not all_values:
            return 0.0

        try:
            return statistics.quantiles(all_values, n=100)[94]
        except statistics.StatisticsError:
            return 0.0

    def _calculate_p95_execution_time(self, timings: dict[str, dict]) -> float:
        """Calculate 95th percentile execution time."""
        if not timings:
            return 0.0

        all_values = []
        for stats in timings.values():
            if "values" in stats:
                all_values.extend(stats["values"])
            else:
                pass

        if not all_values:
            return 0.0

        try:
            return statistics.quantiles(all_values, n=100)[94]
        except statistics.StatisticsError:
            return 0.0

    def _calculate_error_rate(self, metrics: dict[str, Any]) -> float:
        """Calculate API error rate percentage."""
        total_errors = sum(v for k, v in metrics["counters"].items() if "api.calls.error" in k)
        total_calls = sum(v for k, v in metrics["counters"].items() if "api.calls.total" in k)

        if total_calls == 0:
            return 0.0

        return (total_errors / total_calls) * 100

    def _calculate_rpm(self, metrics: dict[str, Any]) -> float:  # noqa: ARG002
        """Calculate requests per minute."""
        # This would require tracking over time intervals
        # Simplified for now
        return 0.0

    def _calculate_avg_execution_time(self, timings: dict[str, dict]) -> float:
        """Calculate average agent execution time."""
        if not timings:
            return 0.0

        total_time = sum(stats["average"] * stats["count"] for stats in timings.values())
        total_count = sum(stats["count"] for stats in timings.values())

        return total_time / total_count if total_count > 0 else 0.0

    def _calculate_success_rate(self, metrics: dict[str, Any], prefix: str) -> float:
        """Calculate success rate percentage."""
        total_success = sum(v for k, v in metrics["counters"].items() if f"{prefix}.success" in k)
        total_attempts = sum(v for k, v in metrics["counters"].items() if f"{prefix}.total" in k)

        if total_attempts == 0:
            return 0.0

        return (total_success / total_attempts) * 100

    def _get_commands_by_type(self, metrics: dict[str, Any]) -> dict[str, int]:
        """Get command counts by type."""
        command_counts = defaultdict(int)

        for k, v in metrics["counters"].items():
            if "agent.executions.total" in k:
                # Extract command type from labels (simplified)
                if "payment" in k:
                    command_counts["payment"] += v
                elif "balance" in k:
                    command_counts["balance"] += v
                elif "trade" in k:
                    command_counts["trade"] += v
                elif "discovery" in k:
                    command_counts["discovery"] += v
                else:
                    command_counts["other"] += v

        return dict(command_counts)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

"""
Prometheus metrics service for Paygent.

This module provides application-wide metrics tracking and exposes
Prometheus-formatted metrics for monitoring and observability.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

from src.services.cache import cache_metrics


@dataclass
class MetricsCollector:
    """Collects and exposes application metrics for Prometheus."""

    # Request metrics
    request_count: int = 0
    request_duration_seconds: float = 0.0
    request_errors: int = 0

    # Agent execution metrics
    agent_executions: int = 0
    agent_executions_success: int = 0
    agent_executions_failed: int = 0
    agent_execution_duration_seconds: float = 0.0

    # Payment metrics
    payments_total: int = 0
    payments_success: int = 0
    payments_failed: int = 0
    payments_total_value_usd: float = 0.0

    # Approval metrics
    approvals_requested: int = 0
    approvals_granted: int = 0
    approvals_denied: int = 0

    # WebSocket metrics
    websocket_connections: int = 0
    websocket_messages_received: int = 0
    websocket_messages_sent: int = 0

    # Session metrics
    sessions_created: int = 0
    sessions_active: int = 0

    # Timing tracking
    start_time: float = field(default_factory=time.time)

    def record_request(self, duration_seconds: float, error: bool = False):
        """Record a request."""
        self.request_count += 1
        self.request_duration_seconds += duration_seconds
        if error:
            self.request_errors += 1

    def record_agent_execution(self, duration_seconds: float, success: bool):
        """Record an agent execution."""
        self.agent_executions += 1
        self.agent_execution_duration_seconds += duration_seconds
        if success:
            self.agent_executions_success += 1
        else:
            self.agent_executions_failed += 1

    def record_payment(self, amount_usd: float, success: bool):
        """Record a payment."""
        self.payments_total += 1
        self.payments_total_value_usd += amount_usd
        if success:
            self.payments_success += 1
        else:
            self.payments_failed += 1

    def record_approval(self, granted: bool):
        """Record an approval decision."""
        self.approvals_requested += 1
        if granted:
            self.approvals_granted += 1
        else:
            self.approvals_denied += 1

    def record_websocket_connection(self):
        """Record a WebSocket connection."""
        self.websocket_connections += 1

    def record_websocket_message(self, received: bool):
        """Record a WebSocket message."""
        if received:
            self.websocket_messages_received += 1
        else:
            self.websocket_messages_sent += 1

    def record_session_created(self):
        """Record a new session."""
        self.sessions_created += 1
        self.sessions_active += 1

    def record_session_terminated(self):
        """Record a session termination."""
        self.sessions_active = max(0, self.sessions_active - 1)

    def get_prometheus_metrics(self) -> str:
        """
        Get all metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        uptime_seconds = time.time() - self.start_time

        # Calculate averages
        avg_request_duration = (
            self.request_duration_seconds / self.request_count
            if self.request_count > 0 else 0.0
        )
        avg_agent_duration = (
            self.agent_execution_duration_seconds / self.agent_executions
            if self.agent_executions > 0 else 0.0
        )

        # Cache metrics from cache service
        cache_stats = cache_metrics.get_stats()

        metrics = [
            "# HELP paygent_uptime_seconds Application uptime in seconds",
            "# TYPE paygent_uptime_seconds gauge",
            f"paygent_uptime_seconds {uptime_seconds:.2f}",
            "",
            "# HELP paygent_request_total Total number of HTTP requests",
            "# TYPE paygent_request_total counter",
            f"paygent_request_total {self.request_count}",
            "",
            "# HELP paygent_request_errors_total Total number of HTTP request errors",
            "# TYPE paygent_request_errors_total counter",
            f"paygent_request_errors_total {self.request_errors}",
            "",
            "# HELP paygent_request_duration_seconds_total Total duration of all requests in seconds",
            "# TYPE paygent_request_duration_seconds_total counter",
            f"paygent_request_duration_seconds_total {self.request_duration_seconds:.3f}",
            "",
            "# HELP paygent_request_duration_seconds Average request duration in seconds",
            "# TYPE paygent_request_duration_seconds gauge",
            f"paygent_request_duration_seconds {avg_request_duration:.3f}",
            "",
            "# HELP paygent_agent_executions_total Total number of agent executions",
            "# TYPE paygent_agent_executions_total counter",
            f"paygent_agent_executions_total {self.agent_executions}",
            "",
            "# HELP paygent_agent_executions_success_total Total successful agent executions",
            "# TYPE paygent_agent_executions_success_total counter",
            f"paygent_agent_executions_success_total {self.agent_executions_success}",
            "",
            "# HELP paygent_agent_executions_failed_total Total failed agent executions",
            "# TYPE paygent_agent_executions_failed_total counter",
            f"paygent_agent_executions_failed_total {self.agent_executions_failed}",
            "",
            "# HELP paygent_agent_execution_duration_seconds Average agent execution duration",
            "# TYPE paygent_agent_execution_duration_seconds gauge",
            f"paygent_agent_execution_duration_seconds {avg_agent_duration:.3f}",
            "",
            "# HELP paygent_payments_total Total number of payments",
            "# TYPE paygent_payments_total counter",
            f"paygent_payments_total {self.payments_total}",
            "",
            "# HELP paygent_payments_success_total Total successful payments",
            "# TYPE paygent_payments_success_total counter",
            f"paygent_payments_success_total {self.payments_success}",
            "",
            "# HELP paygent_payments_failed_total Total failed payments",
            "# TYPE paygent_payments_failed_total counter",
            f"paygent_payments_failed_total {self.payments_failed}",
            "",
            "# HELP paygent_payments_total_value_usd Total value of all payments in USD",
            "# TYPE paygent_payments_total_value_usd counter",
            f"paygent_payments_total_value_usd {self.payments_total_value_usd:.2f}",
            "",
            "# HELP paygent_approvals_requested_total Total number of approval requests",
            "# TYPE paygent_approvals_requested_total counter",
            f"paygent_approvals_requested_total {self.approvals_requested}",
            "",
            "# HELP paygent_approvals_granted_total Total number of approvals granted",
            "# TYPE paygent_approvals_granted_total counter",
            f"paygent_approvals_granted_total {self.approvals_granted}",
            "",
            "# HELP paygent_approvals_denied_total Total number of approvals denied",
            "# TYPE paygent_approvals_denied_total counter",
            f"paygent_approvals_denied_total {self.approvals_denied}",
            "",
            "# HELP paygent_websocket_connections_total Total WebSocket connections",
            "# TYPE paygent_websocket_connections_total counter",
            f"paygent_websocket_connections_total {self.websocket_connections}",
            "",
            "# HELP paygent_websocket_messages_received_total Total WebSocket messages received",
            "# TYPE paygent_websocket_messages_received_total counter",
            f"paygent_websocket_messages_received_total {self.websocket_messages_received}",
            "",
            "# HELP paygent_websocket_messages_sent_total Total WebSocket messages sent",
            "# TYPE paygent_websocket_messages_sent_total counter",
            f"paygent_websocket_messages_sent_total {self.websocket_messages_sent}",
            "",
            "# HELP paygent_sessions_created_total Total sessions created",
            "# TYPE paygent_sessions_created_total counter",
            f"paygent_sessions_created_total {self.sessions_created}",
            "",
            "# HELP paygent_sessions_active Current number of active sessions",
            "# TYPE paygent_sessions_active gauge",
            f"paygent_sessions_active {self.sessions_active}",
            "",
            "# HELP paygent_cache_hits_total Total cache hits",
            "# TYPE paygent_cache_hits_total counter",
            f"paygent_cache_hits_total {cache_stats['hits']}",
            "",
            "# HELP paygent_cache_misses_total Total cache misses",
            "# TYPE paygent_cache_misses_total counter",
            f"paygent_cache_misses_total {cache_stats['misses']}",
            "",
            "# HELP paygent_cache_hit_rate Cache hit rate percentage",
            "# TYPE paygent_cache_hit_rate gauge",
            f"paygent_cache_hit_rate {cache_stats['hit_rate_percent']}",
            "",
            "# HELP paygent_cache_sets_total Total cache set operations",
            "# TYPE paygent_cache_sets_total counter",
            f"paygent_cache_sets_total {cache_stats['sets']}",
            "",
            "# HELP paygent_cache_deletes_total Total cache delete operations",
            "# TYPE paygent_cache_deletes_total counter",
            f"paygent_cache_deletes_total {cache_stats['deletes']}",
            "",
            "# HELP paygent_cache_avg_get_time_ms Average cache get time in milliseconds",
            "# TYPE paygent_cache_avg_get_time_ms gauge",
            f"paygent_cache_avg_get_time_ms {cache_stats['avg_get_time_ms']}",
            "",
            "# HELP paygent_cache_avg_set_time_ms Average cache set time in milliseconds",
            "# TYPE paygent_cache_avg_set_time_ms gauge",
            f"paygent_cache_avg_set_time_ms {cache_stats['avg_set_time_ms']}",
        ]

        return "\n".join(metrics)


# Global metrics collector instance
metrics_collector = MetricsCollector()

"""
Mock Prometheus tools for metrics retrieval.
In production, this would use prometheus-api-client.
"""

from typing import Dict, Any


def get_mock_metrics(service_name: str, alert_type: str) -> Dict[str, Any]:
    """
    Get mock metrics for a service.
    Simulates Prometheus/CloudWatch metrics data.
    """
    
    # Base metrics
    metrics = {
        "service": service_name,
        "cpu_usage": 45,
        "memory_usage": 62,
        "p99_latency": 150,
        "error_rate": 0.5,
        "db_connections": 45,
        "db_pool_size": 100,
        "request_rate": 1500,
    }
    
    # Adjust metrics based on alert type to simulate different scenarios
    if alert_type == "latency_spike":
        metrics.update({
            "p99_latency": 2000,
            "db_connections": 98,
            "db_pool_size": 100,
        })
    elif alert_type == "error_rate":
        metrics.update({
            "error_rate": 15.5,
            "p99_latency": 800,
        })
    elif alert_type == "cpu_spike":
        metrics.update({
            "cpu_usage": 95,
            "memory_usage": 88,
        })
    elif alert_type == "db_connection":
        metrics.update({
            "db_connections": 100,
            "db_pool_size": 100,
            "p99_latency": 1500,
        })
    
    return metrics


def query_prometheus(query: str, time_range: str = "1h") -> Dict[str, Any]:
    """
    Execute a PromQL query (mock implementation).
    
    Args:
        query: PromQL query string
        time_range: Time range for the query
    
    Returns:
        Mock query results
    """
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {"__name__": "up"}, "value": [1640000000, "1"]}
            ]
        }
    }


def get_alerts() -> list:
    """Get current active alerts (mock)."""
    return [
        {
            "alertname": "HighLatency",
            "service": "checkout-service",
            "severity": "critical",
            "description": "p99 latency > 2000ms"
        }
    ]

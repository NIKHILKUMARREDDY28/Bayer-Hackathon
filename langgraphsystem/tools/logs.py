"""
Mock CloudWatch logs tools with LLM summarization for large volumes.
In production, this would use boto3 CloudWatch Logs client.
"""

import os
from typing import List, Optional


# Mock log data for different scenarios
MOCK_LOGS = {
    "latency_spike": [
        "[2026-02-06 12:00:01] ERROR checkout-service - Connection timeout after 30000ms",
        "[2026-02-06 12:00:02] WARN checkout-service - Connection pool nearly exhausted: 98/100",
        "[2026-02-06 12:00:03] ERROR checkout-service - Failed to acquire database connection",
        "[2026-02-06 12:00:04] ERROR checkout-service - java.sql.SQLException: Cannot get a connection, pool exhausted",
        "[2026-02-06 12:00:05] WARN checkout-service - Retry attempt 1/3 for order processing",
        "[2026-02-06 12:00:06] ERROR checkout-service - Connection pool exhausted, waiting for available connection",
        "[2026-02-06 12:00:07] ERROR checkout-service - Request timed out: POST /api/checkout",
        "[2026-02-06 12:00:08] WARN checkout-service - High latency detected: 2150ms for /api/checkout",
        "[2026-02-06 12:00:09] ERROR checkout-service - Database connection timeout - pool size: 100, active: 100",
        "[2026-02-06 12:00:10] INFO checkout-service - Configuration loaded: connection_pool_size=100 (was: 200)",
    ],
    "error_rate": [
        "[2026-02-06 12:00:01] ERROR payment-service - NullPointerException at PaymentProcessor.java:142",
        "[2026-02-06 12:00:02] ERROR payment-service - Transaction failed: Invalid card token",
        "[2026-02-06 12:00:03] ERROR payment-service - 5XX response from payment gateway",
        "[2026-02-06 12:00:04] WARN payment-service - Retrying failed payment request",
        "[2026-02-06 12:00:05] ERROR payment-service - Circuit breaker open for payment-gateway",
    ],
    "cpu_spike": [
        "[2026-02-06 12:00:01] WARN compute-service - CPU usage at 92%",
        "[2026-02-06 12:00:02] WARN compute-service - GC pause: 450ms",
        "[2026-02-06 12:00:03] ERROR compute-service - OOM killer triggered",
        "[2026-02-06 12:00:04] INFO compute-service - Scaling event triggered",
    ],
    "db_connection": [
        "[2026-02-06 12:00:01] ERROR db-proxy - Connection limit reached: 100/100",
        "[2026-02-06 12:00:02] ERROR db-proxy - No available connections in pool",
        "[2026-02-06 12:00:03] WARN db-proxy - Connection wait timeout exceeded",
    ],
}


def get_mock_logs(service_name: str, alert_type: str) -> List[str]:
    """
    Get mock log entries for a service.
    In production, this would stream from CloudWatch.
    """
    return MOCK_LOGS.get(alert_type, [
        f"[2026-02-06 12:00:01] INFO {service_name} - Service running normally",
        f"[2026-02-06 12:00:02] DEBUG {service_name} - Health check passed",
    ])


async def summarize_logs(logs: List[str], chunk_size: int = 500) -> str:
    """
    Summarize logs using LLM (STRATUS pattern for large volumes).
    For hackathon, we use a simpler pattern-based approach.
    
    In production, this would:
    1. Chunk logs into batches
    2. Summarize each chunk with LLM
    3. Combine summaries
    """
    if not logs:
        return "No logs available for analysis."
    
    # Count error patterns
    errors = [log for log in logs if "ERROR" in log]
    warnings = [log for log in logs if "WARN" in log]
    
    # Extract key patterns
    patterns = []
    if any("connection" in log.lower() for log in logs):
        patterns.append("Connection-related issues detected")
    if any("timeout" in log.lower() for log in logs):
        patterns.append("Timeout errors present")
    if any("pool" in log.lower() for log in logs):
        patterns.append("Connection pool issues")
    if any("configuration" in log.lower() or "config" in log.lower() for log in logs):
        patterns.append("Configuration change referenced")
    
    summary = f"""
**Log Summary:**
- Total entries analyzed: {len(logs)}
- Errors: {len(errors)}
- Warnings: {len(warnings)}

**Key Patterns:**
{chr(10).join(f'• {p}' for p in patterns) if patterns else '• No specific patterns detected'}

**Sample Errors:**
{chr(10).join(errors[:3]) if errors else 'No errors found'}
"""
    
    return summary


async def stream_logs_chunked(log_group: str, chunk_size: int = 1000):
    """
    Stream logs in chunks for memory efficiency (async generator).
    This is the hackathon-friendly approach instead of Kafka.
    """
    logs = MOCK_LOGS.get("latency_spike", [])
    for i in range(0, len(logs), chunk_size):
        yield logs[i:i + chunk_size]

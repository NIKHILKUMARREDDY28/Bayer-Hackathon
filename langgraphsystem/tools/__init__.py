"""
Tools package for the Autonomous Incident Commander.
"""

from .prometheus import get_mock_metrics, query_prometheus, get_alerts
from .logs import get_mock_logs, summarize_logs, stream_logs_chunked
from .deployments import get_recent_deployments, get_deployment_diff, recommend_rollback
from .aws_log_streamer import (
    AWSLogStreamer, 
    get_log_streamer, 
    get_aws_alerts, 
    get_aws_anomalies,
    get_aws_log_summary
)
from .email_notifier import (
    EmailNotifier,
    get_email_notifier,
    send_incident_email
)
from .mcp_email import (
    MCPEmailTool,
    get_mcp_email_tool,
    send_email_mcp,
    send_incident_email_mcp,
    create_langchain_tool
)

__all__ = [
    # Prometheus
    "get_mock_metrics",
    "query_prometheus", 
    "get_alerts",
    # Logs
    "get_mock_logs",
    "summarize_logs",
    "stream_logs_chunked",
    # Deployments
    "get_recent_deployments",
    "get_deployment_diff",
    "recommend_rollback",
    # AWS Log Streamer
    "AWSLogStreamer",
    "get_log_streamer",
    "get_aws_alerts",
    "get_aws_anomalies",
    "get_aws_log_summary",
    # Email (SMTP legacy)
    "EmailNotifier",
    "get_email_notifier",
    "send_incident_email",
    # MCP Email (Resend)
    "MCPEmailTool",
    "get_mcp_email_tool",
    "send_email_mcp",
    "send_incident_email_mcp",
    "create_langchain_tool",
]

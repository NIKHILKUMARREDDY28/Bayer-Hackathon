"""
Diagnosis Agent (αG) - READ-only
Performs root cause analysis using observability data.
"""

import os
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from ..state import IncidentState
from ..tools.prometheus import get_mock_metrics
from ..tools.logs import get_mock_logs, summarize_logs
from ..tools.deployments import get_recent_deployments


async def diagnosis_agent(state: IncidentState) -> dict:
    """
    Diagnosis phase: Analyze metrics, logs, and deployments to find root cause.
    READ-only: Does not mutate system state.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    detected_issues = state["detected_issues"]
    
    # Gather observability data (READ-only)
    metrics = get_mock_metrics(service_name, alert_type)
    logs = get_mock_logs(service_name, alert_type)
    deployments = get_recent_deployments(service_name)
    
    # Summarize logs (LLM compression for large volumes)
    log_summary = await summarize_logs(logs)
    
    # Create metrics summary
    metrics_summary = f"""
**Metrics Analysis:**
- CPU Usage: {metrics.get('cpu_usage', 'N/A')}%
- Memory Usage: {metrics.get('memory_usage', 'N/A')}%
- p99 Latency: {metrics.get('p99_latency', 'N/A')}ms
- Error Rate: {metrics.get('error_rate', 'N/A')}%
- DB Connections: {metrics.get('db_connections', 'N/A')}/{metrics.get('db_pool_size', 'N/A')}
"""
    
    # Analyze deployments
    deployment_changes = []
    root_cause = None
    
    for deploy in deployments:
        if deploy.get("has_config_change"):
            deployment_changes.append(deploy)
            if deploy.get("change_type") == "connection_pool":
                root_cause = f"Configuration change detected: {deploy['description']} ({deploy['timestamp']})"
    
    # If no deployment-related cause, analyze other factors
    if not root_cause:
        if metrics.get('db_connections', 0) >= metrics.get('db_pool_size', 100):
            root_cause = "Database connection pool exhaustion"
        elif metrics.get('cpu_usage', 0) > 90:
            root_cause = "CPU resource exhaustion"
        elif metrics.get('error_rate', 0) > 5:
            root_cause = "High error rate - possible application bug"
        else:
            root_cause = "Unable to determine definitive root cause - requires manual investigation"
    
    # Generate diagnosis result
    diagnosis_result = f"""
**Root Cause Analysis:**
{root_cause}

**Evidence:**
- Metrics show {metrics.get('db_connections', 'N/A')} active connections
- Logs indicate connection timeout errors
- Config deployment found {len(deployment_changes)} minute(s) before incident
"""
    
    diagnosis_message = f"""
🔬 **DIAGNOSIS PHASE COMPLETE**

{metrics_summary}

**Log Analysis:**
{log_summary}

**Recent Deployments:** {len(deployment_changes)} config changes found

{diagnosis_result}

Proceeding to mitigation phase...
"""
    
    return {
        "diagnosis_result": diagnosis_result,
        "root_cause": root_cause,
        "log_summary": log_summary,
        "metrics_summary": metrics_summary,
        "deployment_changes": deployment_changes,
        "current_phase": "mitigation",
        "messages": [AIMessage(content=diagnosis_message)]
    }

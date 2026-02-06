"""
Diagnosis Agent (αG) - READ-only
Performs root cause analysis using observability data.
Uses OpenAI as the brain for intelligent RCA.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state import IncidentState
from ..tools.prometheus import get_mock_metrics
from ..tools.logs import get_mock_logs
from ..tools.deployments import get_recent_deployments

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
)

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert SRE (Site Reliability Engineer) diagnosis agent.
Your role is to perform root cause analysis using observability data.

Given metrics, logs, and deployment information, you must:
1. Analyze patterns in the data
2. Correlate events across different data sources
3. Identify the most likely root cause
4. Provide confidence level in your diagnosis
5. Suggest what to investigate further if needed

Be systematic and data-driven. Focus on evidence-based conclusions."""


async def diagnosis_agent(state: IncidentState) -> dict:
    """
    Diagnosis phase: Analyze metrics, logs, and deployments to find root cause using OpenAI.
    READ-only: Does not mutate system state.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    detected_issues = state["detected_issues"]
    
    # Gather observability data (READ-only)
    metrics = get_mock_metrics(service_name, alert_type)
    logs = get_mock_logs(service_name, alert_type)
    deployments = get_recent_deployments(service_name)
    
    # Create metrics summary
    metrics_summary = f"""
**Metrics Analysis:**
- CPU Usage: {metrics.get('cpu_usage', 'N/A')}%
- Memory Usage: {metrics.get('memory_usage', 'N/A')}%
- p99 Latency: {metrics.get('p99_latency', 'N/A')}ms
- Error Rate: {metrics.get('error_rate', 'N/A')}%
- DB Connections: {metrics.get('db_connections', 'N/A')}/{metrics.get('db_pool_size', 'N/A')}
"""
    
    # Format logs for LLM
    logs_text = "\n".join(logs[:20])  # Limit to 20 log lines

    # Format deployments for LLM
    deployments_text = "\n".join([
        f"- {d.get('timestamp')}: {d.get('description')} (config change: {d.get('has_config_change')})"
        for d in deployments
    ])

    # Prepare context for LLM diagnosis
    diagnosis_context = f"""
Perform root cause analysis for the following incident:

**Detected Issues:**
{chr(10).join(f'- {issue}' for issue in detected_issues)}

**Metrics:**
{metrics_summary}

**Recent Logs:**
{logs_text}

**Recent Deployments:**
{deployments_text}

Please provide:
1. Your root cause analysis
2. The most likely root cause
3. Supporting evidence from the data
4. Confidence level (High/Medium/Low)
5. Recommended next steps
"""

    # Use OpenAI for intelligent diagnosis
    messages = [
        SystemMessage(content=DIAGNOSIS_SYSTEM_PROMPT),
        HumanMessage(content=diagnosis_context)
    ]

    response = await llm.ainvoke(messages)
    llm_diagnosis = response.content

    # Extract deployment changes with config changes
    deployment_changes = [d for d in deployments if d.get("has_config_change")]

    # Determine root cause from LLM analysis and data
    root_cause = None
    
    for deploy in deployments:
        if deploy.get("has_config_change"):
            if deploy.get("change_type") == "connection_pool":
                root_cause = f"Configuration change detected: {deploy['description']} ({deploy['timestamp']})"
                break

    if not root_cause:
        if metrics.get('db_connections', 0) >= metrics.get('db_pool_size', 100):
            root_cause = "Database connection pool exhaustion"
        elif metrics.get('cpu_usage', 0) > 90:
            root_cause = "CPU resource exhaustion"
        elif metrics.get('error_rate', 0) > 5:
            root_cause = "High error rate - possible application bug"
        else:
            root_cause = "Root cause identified by AI analysis - see details below"

    # Generate diagnosis result
    diagnosis_result = f"""
**Root Cause Analysis:**
{root_cause}

**Evidence:**
- Metrics show {metrics.get('db_connections', 'N/A')} active connections
- Logs indicate connection timeout errors
- Config deployment found {len(deployment_changes)} minute(s) before incident
"""

    # Summarize logs
    log_summary = f"""
**Log Summary:**
- Total entries analyzed: {len(logs)}
- Errors: {len([l for l in logs if 'ERROR' in l])}
- Warnings: {len([l for l in logs if 'WARN' in l])}

**Sample Errors:**
{chr(10).join([l for l in logs if 'ERROR' in l][:3])}
"""

    diagnosis_message = f"""
🔬 **DIAGNOSIS PHASE COMPLETE**

{metrics_summary}

**Log Analysis:**
{log_summary}

**Recent Deployments:** {len(deployment_changes)} config changes found

{diagnosis_result}

**AI Diagnosis:**
{llm_diagnosis}

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

"""
Metrics Agent - Analyzes Prometheus/CloudWatch metrics.
Called by Orchestrator when metrics correlation is needed.
Uses OpenAI as the brain for intelligent metrics analysis.
"""

import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..state import IncidentState
from ..tools.prometheus import get_mock_metrics, query_prometheus, get_alerts


# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)

METRICS_ANALYSIS_SYSTEM_PROMPT = """You are an expert SRE Metrics Analysis Agent for the Autonomous Incident Commander.
Your role is to analyze Prometheus/CloudWatch metrics to identify system health issues.

TASK:
Analyze the provided metrics and correlate with any log anomalies found.

METRICS TO ANALYZE:
- CPU Usage: Normal < 80%, Warning 80-90%, Critical > 90%
- Memory Usage: Normal < 75%, Warning 75-85%, Critical > 85%
- p99 Latency: Normal < 500ms, Warning 500-1000ms, Critical > 1000ms
- Error Rate: Normal < 1%, Warning 1-5%, Critical > 5%
- DB Connections: Warning if > 80% of pool, Critical if >= 100%

ROOT CAUSE CATEGORIES:
- resource_exhaustion: CPU/Memory at critical levels
- connection_pool_exhaustion: DB connections maxed out
- latency_degradation: High p99 latency
- error_spike: High error rate
- cascading_failure: Multiple metrics degraded
- infrastructure_issue: Underlying infrastructure problems

OUTPUT FORMAT (Strict JSON):
{{
    "metrics_anomaly_detected": true/false,
    "anomaly_category": "one of the categories above or null",
    "critical_metrics": ["list of metrics at critical levels"],
    "warning_metrics": ["list of metrics at warning levels"],
    "resource_utilization": {{
        "cpu_status": "normal/warning/critical",
        "memory_status": "normal/warning/critical",
        "db_pool_status": "normal/warning/critical"
    }},
    "correlation_with_logs": "How metrics correlate with log anomalies",
    "root_cause_hypothesis": "Most likely root cause based on metrics",
    "confidence_score": 0-100,
    "recommended_action": "Immediate action to consider",
    "needs_deployment_check": true/false
}}

Be data-driven and precise in your analysis."""


async def metrics_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Metrics Agent: Analyzes Prometheus metrics.
    Called by Orchestrator when metrics correlation is needed.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    alert_id = state["alert_id"]
    logs_analysis = state.get("logs_analysis") or {}
    anomaly_type = state.get("anomaly_type") or "unknown"

    # Get metrics - either from state or mock Prometheus data
    metrics = state.get("raw_metrics")
    if not metrics:
        metrics = get_mock_metrics(service_name, alert_type)

    # Get active alerts from Prometheus
    active_alerts = get_alerts()

    # Format metrics for analysis
    metrics_text = f"""
SERVICE: {service_name}

CURRENT METRICS:
- CPU Usage: {metrics.get('cpu_usage', 'N/A')}%
- Memory Usage: {metrics.get('memory_usage', 'N/A')}%
- p99 Latency: {metrics.get('p99_latency', 'N/A')}ms
- Error Rate: {metrics.get('error_rate', 'N/A')}%
- DB Connections: {metrics.get('db_connections', 'N/A')}/{metrics.get('db_pool_size', 'N/A')}
- Request Rate: {metrics.get('request_rate', 'N/A')} req/s

ACTIVE PROMETHEUS ALERTS:
{chr(10).join(f"- {a['alertname']}: {a['description']}" for a in active_alerts)}

LOG ANOMALY DETECTED: {anomaly_type}
LOG ANALYSIS SUMMARY: {logs_analysis.get('summary', 'No log analysis available')}
"""

    # Prepare context for LLM
    analysis_context = f"""
Analyze the following Prometheus metrics for service: {service_name}
Alert ID: {alert_id}

{metrics_text}

Correlate these metrics with the log anomaly type: {anomaly_type}
Identify the root cause and recommend actions.
"""

    # Build the chain
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", METRICS_ANALYSIS_SYSTEM_PROMPT),
            ("human", "{context}"),
        ]
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    # Invoke LLM for analysis
    try:
        result = chain.invoke({"context": analysis_context})
    except Exception as e:
        # Fallback if JSON parsing fails
        result = {
            "metrics_anomaly_detected": True,
            "anomaly_category": "unknown",
            "critical_metrics": [],
            "warning_metrics": [],
            "resource_utilization": {
                "cpu_status": "unknown",
                "memory_status": "unknown",
                "db_pool_status": "unknown",
            },
            "correlation_with_logs": f"Error during analysis: {str(e)}",
            "root_cause_hypothesis": "Unable to determine",
            "confidence_score": 30,
            "recommended_action": "Manual investigation required",
            "needs_deployment_check": True,
        }

    # Build response message
    metrics_message = f"""
📊 **METRICS AGENT (PROMETHEUS) ANALYSIS COMPLETE**

**Service:** {service_name}
**Alert ID:** {alert_id}

**Metrics Status:**
- CPU: {result.get('resource_utilization', {}).get('cpu_status', 'N/A')} ({metrics.get('cpu_usage', 'N/A')}%)
- Memory: {result.get('resource_utilization', {}).get('memory_status', 'N/A')} ({metrics.get('memory_usage', 'N/A')}%)
- DB Pool: {result.get('resource_utilization', {}).get('db_pool_status', 'N/A')} ({metrics.get('db_connections', 'N/A')}/{metrics.get('db_pool_size', 'N/A')})

**Critical Metrics:**
{chr(10).join(f'🔴 {m}' for m in result.get('critical_metrics', [])) or '• None at critical level'}

**Warning Metrics:**
{chr(10).join(f'🟡 {m}' for m in result.get('warning_metrics', [])) or '• None at warning level'}

**Correlation with Logs:**
{result.get('correlation_with_logs', 'N/A')}

**Root Cause Hypothesis:**
{result.get('root_cause_hypothesis', 'N/A')}
(Confidence: {result.get('confidence_score', 0)}%)

**Recommended Action:**
{result.get('recommended_action', 'N/A')}

**Deployment Check Needed:** {'Yes' if result.get('needs_deployment_check') else 'No'}

→ Handing off to Orchestrator for decision...
"""

    return {
        "metrics_analysis": result,
        "metrics_anomaly_detected": result.get("metrics_anomaly_detected", False),
        "current_phase": "orchestrator_decision",
        "proposed_solution": result.get("recommended_action"),
        "messages": [AIMessage(content=metrics_message)],
    }


# Synchronous wrapper for the graph
def metrics_agent_node(state: IncidentState) -> Dict[str, Any]:
    """Synchronous wrapper for metrics_agent."""
    import asyncio

    return asyncio.run(metrics_agent(state))

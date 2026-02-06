"""
Logs Agent - Analyzes logs and detects anomalies.
Hands off to Orchestrator for next action decision.
Uses OpenAI as the brain for intelligent log analysis.
"""

import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..state import IncidentState
from ..tools.logs import get_mock_logs

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)

LOGS_ANALYSIS_SYSTEM_PROMPT = """You are an expert SRE Logs Analysis Agent for the Autonomous Incident Commander.
Your role is to analyze application and system logs to detect anomalies and patterns.

TASK:
Analyze the provided logs and identify any anomalies or issues.

ANOMALY CATEGORIES:
- memory_leak: Increasing memory usage patterns, OOM errors
- db_timeout: Database connection timeouts, pool exhaustion
- exception_spike: Unusual increase in exceptions or errors
- latency_spike: High response times, slow requests
- connection_pool: Connection pool exhaustion
- config_change: Configuration-related issues
- isolated_errors: One-off errors that don't indicate systemic issues
- no_anomaly: No significant issues detected

OUTPUT FORMAT (Strict JSON):
{{
    "anomaly_detected": true/false,
    "anomaly_type": "one of the categories above or null",
    "error_count": number,
    "warning_count": number,
    "critical_patterns": ["list of critical patterns found"],
    "timeline": {{
        "first_error": "timestamp or null",
        "last_error": "timestamp or null"
    }},
    "summary": "Brief summary of log analysis",
    "confidence_score": 0-100,
    "needs_metrics_correlation": true/false,
    "reason_for_metrics": "Why metrics analysis would help (or null)"
}}

Be thorough but concise. Focus on actionable insights."""


async def logs_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Logs Agent: Analyzes logs to detect anomalies.
    Hands off to Orchestrator with analysis results.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    alert_id = state["alert_id"]

    # Get logs - either from state or mock data
    logs = state.get("raw_logs", [])
    if not logs:
        logs = get_mock_logs(service_name, alert_type)

    # Format logs for analysis
    logs_text = "\n".join(logs[:50])  # Limit to 50 log entries

    # Prepare context for LLM
    analysis_context = f"""
Analyze the following logs for service: {service_name}
Alert Type: {alert_type}
Alert ID: {alert_id}

LOGS:
{logs_text}

Identify any anomalies, patterns, or issues in these logs.
"""

    # Build the chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", LOGS_ANALYSIS_SYSTEM_PROMPT),
        ("human", "{context}")
    ])

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    # Invoke LLM for analysis
    try:
        result = chain.invoke({"context": analysis_context})
    except Exception as e:
        # Fallback if JSON parsing fails
        result = {
            "anomaly_detected": True,
            "anomaly_type": "unknown",
            "error_count": len([l for l in logs if "ERROR" in l]),
            "warning_count": len([l for l in logs if "WARN" in l]),
            "critical_patterns": [],
            "timeline": {"first_error": None, "last_error": None},
            "summary": f"Error during analysis: {str(e)}",
            "confidence_score": 50,
            "needs_metrics_correlation": True,
            "reason_for_metrics": "Analysis incomplete, need metrics for full picture"
        }

    # Build response message
    logs_message = f"""
📋 **LOGS AGENT ANALYSIS COMPLETE**

**Service:** {service_name}
**Alert ID:** {alert_id}

**Analysis Results:**
- Anomaly Detected: {'✅ YES' if result['anomaly_detected'] else '❌ NO'}
- Anomaly Type: {result.get('anomaly_type', 'N/A')}
- Error Count: {result.get('error_count', 0)}
- Warning Count: {result.get('warning_count', 0)}
- Confidence: {result.get('confidence_score', 0)}%

**Critical Patterns Found:**
{chr(10).join(f'• {p}' for p in result.get('critical_patterns', [])) or '• None detected'}

**Summary:**
{result.get('summary', 'No summary available')}

**Metrics Correlation Needed:** {'Yes - ' + result.get('reason_for_metrics', '') if result.get('needs_metrics_correlation') else 'No'}

→ Handing off to Orchestrator for next action...
"""

    return {
        "logs_analysis": result,
        "anomaly_detected": result.get("anomaly_detected", False),
        "anomaly_type": result.get("anomaly_type"),
        "current_phase": "orchestrator_decision",
        "messages": [AIMessage(content=logs_message)]
    }


# Synchronous wrapper for the graph
def logs_agent_node(state: IncidentState) -> Dict[str, Any]:
    """Synchronous wrapper for logs_agent."""
    import asyncio
    return asyncio.run(logs_agent(state))

"""
Orchestrator Agent - Coordinates all sub-agents in the incident response workflow.
Makes decisions about which agent to call next based on current state.
Uses OpenAI as the brain for intelligent coordination.
"""

import copy
from typing import Dict, Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..state import IncidentState

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
)

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator Agent for the Autonomous Incident Commander.
Your role is to coordinate sub-agents and make decisions about the incident response workflow.

AVAILABLE SUB-AGENTS:
1. logs_agent: Analyzes application/system logs for anomalies
2. metrics_agent: Analyzes Prometheus/CloudWatch metrics
3. deployment_agent: Analyzes CI/CD history and config changes
4. mitigation_agent: Executes remediation actions
5. report_agent: Generates final RCA report

WORKFLOW RULES:
1. Start with logs_agent to detect anomalies
2. If logs show anomaly → call metrics_agent to correlate with Prometheus data
3. If metrics confirm issue AND needs deployment check → call deployment_agent
4. Once root cause is identified with high confidence (>70%) → proceed to mitigation
5. If confidence is low (<50%) → gather more data or escalate
6. After mitigation → generate report

DECISION CRITERIA:
- anomaly_detected: true → investigate further with metrics
- metrics_anomaly_detected: true → check deployment history
- deployment_correlated: true → root cause likely found
- confidence_score > 70: proceed to mitigation
- confidence_score 50-70: may need more data
- confidence_score < 50: manual escalation recommended

OUTPUT FORMAT (Strict JSON):
{{
    "decision": "CALL_METRICS | CALL_DEPLOYMENT | PROCEED_MITIGATION | GENERATE_REPORT | ESCALATE",
    "next_agent": "metrics_agent | deployment_agent | mitigation_agent | report_agent | null",
    "reasoning": "Detailed explanation of why this decision was made",
    "root_cause_summary": "Current understanding of root cause (or null)",
    "confidence_score": 0-100,
    "recommended_action": "What action should be taken",
    "escalation_needed": true/false
}}

Be decisive but data-driven. Ensure all relevant data is gathered before mitigation."""


async def orchestrator_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Orchestrator Agent: Coordinates all sub-agents.
    Makes decisions about workflow based on current state.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    alert_id = state["alert_id"]
    current_phase = state.get("current_phase", "initial")

    # Gather analysis from all agents (ensure dict, not None)
    logs_analysis = state.get("logs_analysis") or {}
    metrics_analysis = state.get("metrics_analysis") or {}
    deployment_analysis = state.get("deployment_analysis") or {}

    anomaly_detected = state.get("anomaly_detected", False)
    metrics_anomaly_detected = state.get("metrics_anomaly_detected", False)
    deployment_correlated = state.get("deployment_correlated", False)

    # Prepare context for LLM decision
    decision_context = f"""
INCIDENT: {alert_id}
SERVICE: {service_name}
ALERT TYPE: {alert_type}
CURRENT PHASE: {current_phase}
SEVERITY: {state.get('severity', 0)}

=== LOGS AGENT ANALYSIS ===
Completed: {'Yes' if logs_analysis else 'No'}
Anomaly Detected: {anomaly_detected}
Anomaly Type: {state.get('anomaly_type', 'N/A')}
Summary: {logs_analysis.get('summary', 'Not analyzed yet')}
Needs Metrics Correlation: {logs_analysis.get('needs_metrics_correlation', 'N/A')}

=== METRICS AGENT (PROMETHEUS) ANALYSIS ===
Completed: {'Yes' if metrics_analysis else 'No'}
Metrics Anomaly: {metrics_anomaly_detected}
Root Cause Hypothesis: {metrics_analysis.get('root_cause_hypothesis', 'Not analyzed yet')}
Confidence: {metrics_analysis.get('confidence_score', 0)}%
Needs Deployment Check: {metrics_analysis.get('needs_deployment_check', 'N/A')}

=== DEPLOYMENT AGENT ANALYSIS ===
Completed: {'Yes' if deployment_analysis else 'No'}
Deployment Correlated: {deployment_correlated}
Suspect Deployment: {deployment_analysis.get('correlated_deployment_id', 'Not analyzed yet')}
Rollback Recommended: {deployment_analysis.get('rollback_recommended', 'N/A')}
Confidence: {deployment_analysis.get('confidence_score', 0)}%

=== CURRENT STATE ===
Proposed Solution: {state.get('proposed_solution', 'None yet')}
Retry Count: {state.get('retry_count', 0)}/{state.get('max_retries', 3)}

Based on this information, decide the next action in the workflow.
"""

    # Build the chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", ORCHESTRATOR_SYSTEM_PROMPT),
        ("human", "{context}")
    ])

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    # Invoke LLM for decision
    try:
        result = chain.invoke({"context": decision_context})
    except Exception as e:
        # Fallback decision logic
        result = _fallback_decision(state, str(e))

    # Map decision to next phase
    decision = result.get("decision", "ESCALATE")
    next_agent = result.get("next_agent")

    if decision == "CALL_METRICS":
        next_phase = "metrics_analysis"
    elif decision == "CALL_DEPLOYMENT":
        next_phase = "deployment_analysis"
    elif decision == "PROCEED_MITIGATION":
        next_phase = "mitigation"
    elif decision == "GENERATE_REPORT":
        next_phase = "report"
    else:
        next_phase = "escalation"

    # Determine root cause from all analyses
    root_cause = _determine_root_cause(state, result)

    # Build orchestrator message
    orchestrator_message = f"""
🎯 **ORCHESTRATOR DECISION**

**Incident:** {alert_id}
**Service:** {service_name}

**Analysis Summary:**
- Logs Analyzed: {'✅' if logs_analysis else '❌'}
- Metrics Analyzed: {'✅' if metrics_analysis else '❌'}
- Deployment Analyzed: {'✅' if deployment_analysis else '❌'}

**Decision:** {decision}
**Next Agent:** {next_agent or 'N/A'}

**Reasoning:**
{result.get('reasoning', 'No reasoning provided')}

**Root Cause Summary:**
{result.get('root_cause_summary', 'Still investigating...')}

**Confidence:** {result.get('confidence_score', 0)}%
**Recommended Action:** {result.get('recommended_action', 'N/A')}
**Escalation Needed:** {'Yes' if result.get('escalation_needed') else 'No'}

→ Proceeding to: {next_phase}...
"""

    return {
        "current_phase": next_phase,
        "next_agent": next_agent,
        "orchestrator_reasoning": result.get("reasoning"),
        "root_cause": root_cause,
        "confidence_score": result.get("confidence_score", 0),
        "proposed_solution": result.get("recommended_action") or state.get("proposed_solution"),
        "messages": [AIMessage(content=orchestrator_message)]
    }


def _fallback_decision(state: IncidentState, error: str) -> Dict[str, Any]:
    """Fallback decision logic when LLM fails."""
    logs_analysis = state.get("logs_analysis") or {}
    metrics_analysis = state.get("metrics_analysis") or {}
    deployment_analysis = state.get("deployment_analysis") or {}
    anomaly_detected = state.get("anomaly_detected", False)

    # Simple rule-based fallback
    if not logs_analysis:
        return {
            "decision": "CALL_LOGS",
            "next_agent": "logs_agent",
            "reasoning": f"Fallback: Starting with logs analysis. Error: {error}",
            "root_cause_summary": None,
            "confidence_score": 0,
            "recommended_action": "Analyze logs first",
            "escalation_needed": False
        }
    elif anomaly_detected and not metrics_analysis:
        return {
            "decision": "CALL_METRICS",
            "next_agent": "metrics_agent",
            "reasoning": f"Fallback: Anomaly detected, need metrics correlation. Error: {error}",
            "root_cause_summary": None,
            "confidence_score": 30,
            "recommended_action": "Check Prometheus metrics",
            "escalation_needed": False
        }
    elif metrics_analysis and not deployment_analysis:
        return {
            "decision": "CALL_DEPLOYMENT",
            "next_agent": "deployment_agent",
            "reasoning": f"Fallback: Need deployment correlation. Error: {error}",
            "root_cause_summary": metrics_analysis.get("root_cause_hypothesis"),
            "confidence_score": 50,
            "recommended_action": "Check recent deployments",
            "escalation_needed": False
        }
    else:
        return {
            "decision": "PROCEED_MITIGATION",
            "next_agent": "mitigation_agent",
            "reasoning": f"Fallback: All data gathered, proceeding to mitigation. Error: {error}",
            "root_cause_summary": "Based on available analysis",
            "confidence_score": 60,
            "recommended_action": "Execute mitigation",
            "escalation_needed": False
        }


def _determine_root_cause(state: IncidentState, orchestrator_result: Dict) -> str:
    """Determine root cause from all agent analyses."""
    # Priority: orchestrator > deployment > metrics > logs
    if orchestrator_result.get("root_cause_summary"):
        return orchestrator_result["root_cause_summary"]

    deployment_analysis = state.get("deployment_analysis") or {}
    if deployment_analysis.get("deployment_correlated"):
        return f"Deployment Issue: {deployment_analysis.get('correlation_evidence', 'Config change correlated')}"

    metrics_analysis = state.get("metrics_analysis") or {}
    if metrics_analysis.get("root_cause_hypothesis"):
        return metrics_analysis["root_cause_hypothesis"]

    logs_analysis = state.get("logs_analysis") or {}
    if logs_analysis.get("summary"):
        return f"Log Analysis: {logs_analysis['summary']}"

    return "Root cause still under investigation"


# Synchronous wrapper for the graph
def orchestrator_agent_node(state: IncidentState) -> Dict[str, Any]:
    """Synchronous wrapper for orchestrator_agent."""
    import asyncio
    return asyncio.run(orchestrator_agent(state))


def orchestrator_router(state: IncidentState) -> Literal["metrics_agent", "deployment_agent", "mitigation", "report", "escalation"]:
    """Router function for conditional edges from orchestrator."""
    next_phase = state.get("current_phase", "escalation")

    if next_phase == "metrics_analysis":
        return "metrics_agent"
    elif next_phase == "deployment_analysis":
        return "deployment_agent"
    elif next_phase == "mitigation":
        return "mitigation"
    elif next_phase == "report":
        return "report"
    else:
        return "escalation"

"""
LangGraph workflow definition for Autonomous Incident Commander.
Implements Orchestrator-based coordination pattern:
- Logs Agent → Orchestrator → Metrics Agent (if anomaly) → Orchestrator → Deployment Agent → Mitigation → Report
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import IncidentState
from .agents.logs_agent import logs_agent
from .agents.metrics_agent import metrics_agent
from .agents.deployment_agent import deployment_agent
from .agents.orchestrator import orchestrator_agent, orchestrator_router
from .agents.mitigation import mitigation_agent
from .agents.undo import undo_agent
from .agents.report import report_agent


def orchestrator_decision_router(state: IncidentState) -> Literal["metrics_agent", "deployment_agent", "mitigation", "report", "escalation"]:
    """
    Router function for conditional edges from orchestrator.
    Decides which agent to call next based on orchestrator decision.
    """
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


def mitigation_decision_router(state: IncidentState) -> Literal["undo", "report"]:
    """
    Router after mitigation: go to undo (retry) or report (success).
    """
    if state.get("health_check_passed", False):
        return "report"
    elif state.get("retry_count", 0) < state.get("max_retries", 3):
        return "undo"
    else:
        return "report"  # Max retries reached, generate failure report


def undo_decision_router(state: IncidentState) -> Literal["orchestrator", "report"]:
    """
    Router after undo: go back to orchestrator for retry or report if max retries.
    """
    if state.get("current_phase") == "report":
        return "report"
    else:
        return "orchestrator"


async def escalation_agent(state: IncidentState) -> dict:
    """
    Escalation node: Called when orchestrator decides manual intervention is needed.
    """
    from langchain_core.messages import AIMessage

    escalation_message = f"""
🚨 **ESCALATION REQUIRED**

**Incident:** {state['alert_id']}
**Service:** {state['service_name']}
**Severity:** {state['severity']:.2f}

**Reason:** Orchestrator determined that automated resolution is not possible.

**Analysis Summary:**
- Logs Anomaly: {state.get('anomaly_type', 'N/A')}
- Root Cause: {state.get('root_cause', 'Unable to determine')}
- Confidence: {state.get('confidence_score', 0)}%

**Recommended Actions:**
1. Review the incident details manually
2. Check recent deployments and configuration changes
3. Engage on-call engineer for investigation

→ Generating incident report for handoff...
"""

    return {
        "current_phase": "report",
        "health_check_passed": False,
        "messages": [AIMessage(content=escalation_message)]
    }


def build_incident_graph():
    """
    Build the LangGraph state machine with Orchestrator-based coordination.

    Flow:
    1. Logs Agent - Analyzes logs for anomalies
    2. Orchestrator - Decides next action (call metrics, deployment, or proceed)
    3. Metrics Agent - Analyzes Prometheus metrics (if needed)
    4. Orchestrator - Decides next action
    5. Deployment Agent - Correlates with CI/CD history (if needed)
    6. Orchestrator - Final decision
    7. Mitigation Agent - Executes remediation
    8. Undo Agent - Rollback if mitigation fails
    9. Report Agent - Generates RCA
    """
    graph = StateGraph(IncidentState)
    
    # Add all agent nodes
    graph.add_node("logs_agent", logs_agent)
    graph.add_node("orchestrator", orchestrator_agent)
    graph.add_node("metrics_agent", metrics_agent)
    graph.add_node("deployment_agent", deployment_agent)
    graph.add_node("mitigation", mitigation_agent)
    graph.add_node("undo", undo_agent)
    graph.add_node("report", report_agent)
    graph.add_node("escalation", escalation_agent)

    # Set entry point - start with logs analysis
    graph.set_entry_point("logs_agent")

    # Logs Agent → Orchestrator (always)
    graph.add_edge("logs_agent", "orchestrator")

    # Orchestrator → conditional routing based on decision
    graph.add_conditional_edges(
        "orchestrator",
        orchestrator_decision_router,
        {
            "metrics_agent": "metrics_agent",
            "deployment_agent": "deployment_agent",
            "mitigation": "mitigation",
            "report": "report",
            "escalation": "escalation"
        }
    )

    # Metrics Agent → Orchestrator (for next decision)
    graph.add_edge("metrics_agent", "orchestrator")

    # Deployment Agent → Orchestrator (for next decision)
    graph.add_edge("deployment_agent", "orchestrator")

    # Mitigation → conditional routing (success → report, failure → undo)
    graph.add_conditional_edges(
        "mitigation",
        mitigation_decision_router,
        {
            "undo": "undo",
            "report": "report"
        }
    )
    
    # Undo → conditional routing (retry → orchestrator, max retries → report)
    graph.add_conditional_edges(
        "undo",
        undo_decision_router,
        {
            "orchestrator": "orchestrator",
            "report": "report"
        }
    )

    # Escalation → Report (generate incident report for handoff)
    graph.add_edge("escalation", "report")

    # Report → END
    graph.add_edge("report", END)
    
    # Compile with memory checkpointer for state persistence
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# Create the compiled graph
incident_graph = build_incident_graph()

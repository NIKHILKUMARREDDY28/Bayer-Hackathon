"""
LangGraph workflow definition for Autonomous Incident Commander.
Implements STRATUS state machine: Detection → Diagnosis → Mitigation → Validate → (Undo|Report)
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import IncidentState
from .agents.detection import detection_agent
from .agents.diagnosis import diagnosis_agent
from .agents.mitigation import mitigation_agent
from .agents.undo import undo_agent
from .agents.report import report_agent


def should_retry_or_report(state: IncidentState) -> Literal["undo", "report"]:
    """
    Validation routing: commit or abort (TNR pattern).
    If health check fails and retries available, go to undo.
    """
    if state["health_check_passed"]:
        return "report"
    elif state["retry_count"] < state["max_retries"]:
        return "undo"
    else:
        # Max retries reached, generate report with failure status
        return "report"


def build_incident_graph():
    """
    Build the LangGraph state machine for incident response.
    
    Flow:
    1. Detection (αD) - READ-only: Identify failures from alerts
    2. Diagnosis (αG) - READ-only: Root cause analysis
    3. Mitigation (αM) - WRITE: Execute remediation (with checkpoint)
    4. Validate - Check if severity decreased
    5. Undo (αU) - WRITE: Rollback on failure
    6. Report - Generate RCA
    """
    graph = StateGraph(IncidentState)
    
    # Add agent nodes
    graph.add_node("detection", detection_agent)
    graph.add_node("diagnosis", diagnosis_agent)
    graph.add_node("mitigation", mitigation_agent)
    graph.add_node("undo", undo_agent)
    graph.add_node("report", report_agent)
    
    # Set entry point
    graph.set_entry_point("detection")
    
    # Define edges (state machine transitions)
    graph.add_edge("detection", "diagnosis")
    graph.add_edge("diagnosis", "mitigation")
    
    # Conditional edge: validate result and decide commit/abort
    graph.add_conditional_edges(
        "mitigation",
        should_retry_or_report,
        {
            "undo": "undo",
            "report": "report"
        }
    )
    
    # Undo loops back to diagnosis for retry
    graph.add_edge("undo", "diagnosis")
    
    # Report ends the workflow
    graph.add_edge("report", END)
    
    # Compile with memory checkpointer for state persistence
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# Create the compiled graph
incident_graph = build_incident_graph()

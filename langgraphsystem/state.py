"""
State management for the Autonomous Incident Commander multi-agent system.
Based on STRATUS paper patterns with TypedDict for type safety.
"""

from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class IncidentState(TypedDict):
    """
    Shared state for all agents in the incident response graph.
    
    Follows STRATUS patterns:
    - αD (Detection) and αG (Diagnosis) only READ state
    - αM (Mitigation) can WRITE state
    - αU (Undo) can restore checkpoint
    """
    
    # Core conversation
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Alert information
    alert_id: str
    alert_type: str
    severity: float  # µ(s) - severity metric (0 = healthy, 1 = critical)
    service_name: str
    
    # Detection phase
    detected_issues: List[str]
    
    # Diagnosis phase  
    diagnosis_result: Optional[str]
    root_cause: Optional[str]
    log_summary: Optional[str]
    metrics_summary: Optional[str]
    deployment_changes: List[dict]
    
    # Mitigation phase
    checkpoint_state: Optional[dict]  # For rollback (TNR pattern)
    mitigation_plan: List[str]
    actions_executed: List[dict]
    
    # Validation
    health_check_passed: bool
    retry_count: int
    max_retries: int
    
    # Final output
    rca_report: Optional[str]
    current_phase: str  # detection, diagnosis, mitigation, validate, undo, report


def create_initial_state(
    alert_id: str,
    alert_type: str,
    severity: float,
    service_name: str
) -> IncidentState:
    """Create initial state for a new incident."""
    return IncidentState(
        messages=[],
        alert_id=alert_id,
        alert_type=alert_type,
        severity=severity,
        service_name=service_name,
        detected_issues=[],
        diagnosis_result=None,
        root_cause=None,
        log_summary=None,
        metrics_summary=None,
        deployment_changes=[],
        checkpoint_state=None,
        mitigation_plan=[],
        actions_executed=[],
        health_check_passed=False,
        retry_count=0,
        max_retries=3,
        rca_report=None,
        current_phase="detection"
    )

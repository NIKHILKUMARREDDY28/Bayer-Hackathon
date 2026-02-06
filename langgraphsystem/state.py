"""
State management for the Autonomous Incident Commander multi-agent system.
Refactored for Orchestrator-based coordination pattern.
"""

from typing import TypedDict, List, Optional, Annotated, Literal
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class IncidentState(TypedDict):
    """
    Shared state for all agents in the incident response graph.
    
    Orchestrator Pattern:
    - Orchestrator coordinates all sub-agents
    - Logs Agent detects anomalies and hands off to Orchestrator
    - Orchestrator decides to call Metrics Agent (Prometheus) if needed
    - Orchestrator makes final decisions on mitigation
    """
    
    # Core conversation
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Alert information
    alert_id: str
    alert_type: str
    severity: float  # µ(s) - severity metric (0 = healthy, 1 = critical)
    service_name: str
    
    # Raw data inputs
    raw_logs: List[str]
    raw_metrics: Optional[dict]
    deployment_history: List[dict]

    # Logs Agent output
    logs_analysis: Optional[dict]
    anomaly_detected: bool
    anomaly_type: Optional[str]  # memory_leak, db_timeout, exception_spike, latency_spike, etc.

    # Metrics Agent output (Prometheus)
    metrics_analysis: Optional[dict]
    metrics_anomaly_detected: bool

    # Deployment Agent output
    deployment_analysis: Optional[dict]
    deployment_correlated: bool

    # Orchestrator decisions
    current_phase: str  # logs_analysis, metrics_analysis, deployment_analysis, diagnosis, mitigation, report
    next_agent: Optional[str]  # Which agent to call next
    orchestrator_reasoning: Optional[str]  # Why orchestrator made this decision

    # Diagnosis (combined from all agents)
    root_cause: Optional[str]
    diagnosis_result: Optional[str]
    confidence_score: float

    # Mitigation phase
    checkpoint_state: Optional[dict]  # For rollback (TNR pattern)
    mitigation_plan: List[str]
    proposed_solution: Optional[str]
    actions_executed: List[dict]
    
    # Validation
    health_check_passed: bool
    retry_count: int
    max_retries: int
    
    # Final output
    rca_report: Optional[str]


def create_initial_state(
    alert_id: str,
    alert_type: str,
    severity: float,
    service_name: str,
    raw_logs: List[str] = None,
    raw_metrics: dict = None,
    deployment_history: List[dict] = None
) -> IncidentState:
    """Create initial state for a new incident."""
    return IncidentState(
        messages=[],
        alert_id=alert_id,
        alert_type=alert_type,
        severity=severity,
        service_name=service_name,
        raw_logs=raw_logs or [],
        raw_metrics=raw_metrics,
        deployment_history=deployment_history or [],
        logs_analysis=None,
        anomaly_detected=False,
        anomaly_type=None,
        metrics_analysis=None,
        metrics_anomaly_detected=False,
        deployment_analysis=None,
        deployment_correlated=False,
        current_phase="logs_analysis",
        next_agent=None,
        orchestrator_reasoning=None,
        root_cause=None,
        diagnosis_result=None,
        confidence_score=0.0,
        checkpoint_state=None,
        mitigation_plan=[],
        proposed_solution=None,
        actions_executed=[],
        health_check_passed=False,
        retry_count=0,
        max_retries=3,
        rca_report=None
    )

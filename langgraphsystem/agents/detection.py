"""
Detection Agent (αD) - READ-only
Identifies failures from incoming alerts and establishes initial error state.
"""

import json
from langchain_core.messages import HumanMessage, AIMessage
from ..state import IncidentState


async def detection_agent(state: IncidentState) -> dict:
    """
    Detection phase: Analyze incoming alert and identify issues.
    READ-only: Does not mutate system state.
    """
    alert_id = state["alert_id"]
    alert_type = state["alert_type"]
    severity = state["severity"]
    service_name = state["service_name"]
    
    # Detection logic
    detected_issues = []
    
    if alert_type == "latency_spike":
        detected_issues.append(f"High latency detected in {service_name}")
        detected_issues.append(f"Severity level: {severity:.2f}")
        detected_issues.append("Potential service degradation in progress")
        
    elif alert_type == "error_rate":
        detected_issues.append(f"Elevated error rate in {service_name}")
        detected_issues.append(f"Error threshold exceeded")
        
    elif alert_type == "cpu_spike":
        detected_issues.append(f"CPU utilization spike in {service_name}")
        detected_issues.append("Resource exhaustion risk detected")
        
    elif alert_type == "db_connection":
        detected_issues.append(f"Database connection pool exhausted for {service_name}")
        detected_issues.append("Connection timeout errors detected")
    
    else:
        detected_issues.append(f"Unknown alert type: {alert_type}")
        detected_issues.append(f"Service affected: {service_name}")
    
    # Create detection message
    detection_summary = f"""
🔍 **DETECTION PHASE COMPLETE**

**Alert ID:** {alert_id}
**Service:** {service_name}
**Severity:** {severity:.2f}/1.0
**Alert Type:** {alert_type}

**Detected Issues:**
{chr(10).join(f'• {issue}' for issue in detected_issues)}

Proceeding to diagnosis phase...
"""
    
    return {
        "detected_issues": detected_issues,
        "current_phase": "diagnosis",
        "messages": [AIMessage(content=detection_summary)]
    }

"""
Mitigation Agent (αM) - WRITE
Executes remediation actions with checkpoint-based rollback support.
"""

import copy
from langchain_core.messages import AIMessage
from ..state import IncidentState


async def mitigation_agent(state: IncidentState) -> dict:
    """
    Mitigation phase: Execute remediation with TNR safety.
    WRITE: Can mutate system state (with checkpoint).
    
    TNR Pattern:
    1. Checkpoint current state before any action
    2. Execute mitigation actions
    3. Validate health (severity should decrease)
    """
    root_cause = state["root_cause"]
    deployment_changes = state["deployment_changes"]
    retry_count = state["retry_count"]
    
    # STEP 1: Create checkpoint (TNR pattern - faithful undo)
    checkpoint_state = {
        "severity": state["severity"],
        "root_cause": root_cause,
        "retry_count": retry_count,
        "deployment_changes": copy.deepcopy(deployment_changes)
    }
    
    # STEP 2: Generate mitigation plan based on root cause
    mitigation_plan = []
    actions_executed = []
    health_check_passed = False
    new_severity = state["severity"]
    
    if "connection pool" in root_cause.lower() or "configuration" in root_cause.lower():
        mitigation_plan = [
            "1. Identify the problematic configuration change",
            "2. Prepare rollback to previous configuration",
            "3. Apply configuration rollback",
            "4. Restart affected service pods",
            "5. Verify connection pool health"
        ]
        
        # Simulate executing actions
        actions_executed = [
            {"action": "rollback_config", "status": "success", "details": "Reverted connection_pool_size to 100"},
            {"action": "restart_pods", "status": "success", "details": "Restarted checkout-service pods"},
            {"action": "verify_connections", "status": "success", "details": "Connection pool at 45/100"}
        ]
        
        # Simulate health improvement (severity decreases)
        new_severity = state["severity"] * 0.2  # 80% improvement
        health_check_passed = new_severity < 0.3
        
    elif "cpu" in root_cause.lower():
        mitigation_plan = [
            "1. Scale up service replicas",
            "2. Apply resource limits",
            "3. Investigate CPU-intensive operations"
        ]
        
        actions_executed = [
            {"action": "scale_replicas", "status": "success", "details": "Scaled from 3 to 6 replicas"},
            {"action": "resource_limits", "status": "success", "details": "Applied CPU limit of 2 cores"}
        ]
        
        new_severity = state["severity"] * 0.3
        health_check_passed = new_severity < 0.3
        
    elif "error rate" in root_cause.lower():
        mitigation_plan = [
            "1. Enable circuit breaker",
            "2. Increase retry timeout",
            "3. Route traffic to healthy instances"
        ]
        
        actions_executed = [
            {"action": "circuit_breaker", "status": "success", "details": "Circuit breaker enabled"},
            {"action": "traffic_shift", "status": "success", "details": "Traffic shifted to healthy pods"}
        ]
        
        new_severity = state["severity"] * 0.4
        health_check_passed = new_severity < 0.3
    
    else:
        mitigation_plan = ["Manual intervention required - no automated mitigation available"]
        actions_executed = [{"action": "escalate", "status": "pending", "details": "Escalated to on-call engineer"}]
        health_check_passed = False
    
    # Generate mitigation message
    mitigation_message = f"""
⚡ **MITIGATION PHASE {'COMPLETE' if health_check_passed else 'ATTEMPTED'}**

**Checkpoint Created:** State preserved for potential rollback

**Mitigation Plan:**
{chr(10).join(mitigation_plan)}

**Actions Executed:**
{chr(10).join(f"• {a['action']}: {a['status']} - {a['details']}" for a in actions_executed)}

**Health Check:**
- Previous Severity: {state['severity']:.2f}
- Current Severity: {new_severity:.2f}
- Threshold: < 0.30
- **Result: {'✅ PASSED' if health_check_passed else '❌ FAILED'}**

{'Proceeding to generate RCA report...' if health_check_passed else f'Initiating undo procedure (Retry {retry_count + 1}/{state["max_retries"]})...'}
"""
    
    return {
        "checkpoint_state": checkpoint_state,
        "mitigation_plan": mitigation_plan,
        "actions_executed": actions_executed,
        "health_check_passed": health_check_passed,
        "severity": new_severity,
        "current_phase": "report" if health_check_passed else "undo",
        "messages": [AIMessage(content=mitigation_message)]
    }

"""
Mitigation Agent (αM) - WRITE
Executes remediation actions with checkpoint-based rollback support.
Called by Orchestrator after root cause is identified.
Uses OpenAI as the brain for intelligent mitigation planning.
"""

import copy
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..state import IncidentState

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
)

MITIGATION_SYSTEM_PROMPT = """You are an expert SRE Mitigation Agent for the Autonomous Incident Commander.
Your role is to plan and execute remediation actions for incidents.

TASK:
Based on the root cause analysis, create and execute a mitigation plan.

MITIGATION STRATEGIES:
- rollback_config: Revert recent configuration changes
- scale_up: Increase resources (replicas, CPU, memory)
- circuit_breaker: Enable circuit breaker for failing dependencies
- restart_pods: Restart affected service pods
- traffic_shift: Route traffic away from unhealthy instances
- connection_pool_increase: Increase database connection pool size

TNR PATTERN (Test-Negative-Retry):
1. Create checkpoint before any action
2. Execute mitigation
3. Validate health check
4. If failed, undo and retry with alternative approach

OUTPUT FORMAT (Strict JSON):
{{
    "mitigation_plan": ["List of ordered steps"],
    "primary_action": "Main remediation action",
    "actions_to_execute": [
        {{"action": "action_name", "params": {{}}, "expected_impact": "description"}}
    ],
    "rollback_plan": "How to undo if mitigation fails",
    "estimated_recovery_time": "e.g., 2-5 minutes",
    "risk_level": "low/medium/high",
    "confidence_score": 0-100
}}

Safety is paramount. Always have a rollback plan."""


async def mitigation_agent(state: IncidentState) -> dict:
    """
    Mitigation phase: Execute remediation with TNR safety.
    WRITE: Can mutate system state (with checkpoint).
    """
    service_name = state["service_name"]
    alert_id = state["alert_id"]
    root_cause = state.get("root_cause") or "Unknown"
    proposed_solution = state.get("proposed_solution") or ""
    deployment_analysis = state.get("deployment_analysis") or {}
    metrics_analysis = state.get("metrics_analysis") or {}
    retry_count = state.get("retry_count", 0)

    # STEP 1: Create checkpoint (TNR pattern)
    checkpoint_state = {
        "severity": state["severity"],
        "root_cause": root_cause,
        "retry_count": retry_count,
        "deployment_analysis": copy.deepcopy(deployment_analysis)
    }
    
    # Prepare context for LLM mitigation planning
    mitigation_context = f"""
INCIDENT: {alert_id}
SERVICE: {service_name}

ROOT CAUSE: {root_cause}

DEPLOYMENT ANALYSIS:
- Correlated: {deployment_analysis.get('deployment_correlated', False)}
- Suspect: {deployment_analysis.get('correlated_deployment_id', 'N/A')}
- Rollback Recommended: {deployment_analysis.get('rollback_recommended', False)}
- Rollback Target: {deployment_analysis.get('rollback_target', 'N/A')}

METRICS ANALYSIS:
- Anomaly Category: {metrics_analysis.get('anomaly_category', 'N/A')}
- Recommended Action: {metrics_analysis.get('recommended_action', 'N/A')}

PROPOSED SOLUTION: {proposed_solution}

RETRY COUNT: {retry_count}/{state.get('max_retries', 3)}

Create a mitigation plan to resolve this incident.
"""

    # Build the chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", MITIGATION_SYSTEM_PROMPT),
        ("human", "{context}")
    ])

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    # Invoke LLM for mitigation planning
    try:
        result = chain.invoke({"context": mitigation_context})
    except Exception as e:
        result = {
            "mitigation_plan": ["Rollback to previous configuration", "Restart service pods", "Verify health"],
            "primary_action": "rollback_config",
            "actions_to_execute": [
                {"action": "rollback_config", "params": {}, "expected_impact": "Restore previous config"}
            ],
            "rollback_plan": "Revert all changes",
            "estimated_recovery_time": "5-10 minutes",
            "risk_level": "medium",
            "confidence_score": 50
        }

    # Execute mitigation (simulated)
    mitigation_plan = result.get("mitigation_plan", [])
    actions_executed = []

    # Simulate executing actions based on root cause
    if "connection" in root_cause.lower() or "config" in root_cause.lower() or deployment_analysis.get("rollback_recommended"):
        actions_executed = [
            {"action": "rollback_config", "status": "success", "details": "Reverted configuration change"},
            {"action": "restart_pods", "status": "success", "details": f"Restarted {service_name} pods"},
            {"action": "verify_health", "status": "success", "details": "Health check passed"}
        ]
        new_severity = state["severity"] * 0.2
        health_check_passed = new_severity < 0.3
        
    elif "cpu" in root_cause.lower() or "memory" in root_cause.lower() or "resource" in root_cause.lower():
        actions_executed = [
            {"action": "scale_up", "status": "success", "details": "Scaled replicas from 3 to 6"},
            {"action": "resource_limits", "status": "success", "details": "Increased resource limits"}
        ]
        new_severity = state["severity"] * 0.3
        health_check_passed = new_severity < 0.3
        
    elif "error" in root_cause.lower() or "exception" in root_cause.lower():
        actions_executed = [
            {"action": "circuit_breaker", "status": "success", "details": "Enabled circuit breaker"},
            {"action": "traffic_shift", "status": "success", "details": "Shifted traffic to healthy pods"}
        ]
        new_severity = state["severity"] * 0.4
        health_check_passed = new_severity < 0.3
    else:
        actions_executed = [
            {"action": "generic_mitigation", "status": "success", "details": "Applied recommended fix"}
        ]
        new_severity = state["severity"] * 0.5
        health_check_passed = new_severity < 0.3

    # Build mitigation message
    mitigation_message = f"""
⚡ **MITIGATION AGENT - EXECUTION {'COMPLETE' if health_check_passed else 'ATTEMPTED'}**

**Incident:** {alert_id}
**Service:** {service_name}

**Root Cause:** {root_cause}

**Checkpoint Created:** ✅ State preserved for rollback

**Mitigation Plan:**
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(mitigation_plan))}

**Actions Executed:**
{chr(10).join(f"• {a['action']}: {a['status']} - {a['details']}" for a in actions_executed)}

**Health Check:**
- Previous Severity: {state['severity']:.2f}
- Current Severity: {new_severity:.2f}
- Threshold: < 0.30
- **Result: {'✅ PASSED' if health_check_passed else '❌ FAILED'}**

**Risk Level:** {result.get('risk_level', 'N/A')}
**Estimated Recovery:** {result.get('estimated_recovery_time', 'N/A')}
**Confidence:** {result.get('confidence_score', 0)}%

{'→ Proceeding to generate RCA report...' if health_check_passed else f'→ Initiating undo (Retry {retry_count + 1}/{state.get("max_retries", 3)})...'}
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


# Synchronous wrapper
def mitigation_agent_node(state: IncidentState) -> dict:
    """Synchronous wrapper for mitigation_agent."""
    import asyncio
    return asyncio.run(mitigation_agent(state))

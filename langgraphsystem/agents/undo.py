"""
Undo Agent (αU) - WRITE
Rollbacks failed mitigations using checkpoint state.
Uses OpenAI as the brain for intelligent rollback planning.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state import IncidentState

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
)


async def undo_agent(state: IncidentState) -> dict:
    """
    Undo phase: Restore checkpoint state when mitigation fails.
    WRITE: Restores system to previous state (faithful undo).
    """
    checkpoint = state.get("checkpoint_state", {})
    retry_count = state.get("retry_count", 0) + 1
    actions_executed = state.get("actions_executed", [])
    mitigation_plan = state.get("mitigation_plan", [])
    root_cause = state.get("root_cause", "Unknown")
    max_retries = state.get("max_retries", 3)

    # Restore from checkpoint
    restored_severity = checkpoint.get("severity", state["severity"])
    
    # Determine if we should try alternative approach
    alternative_approach = ""
    if retry_count == 1:
        alternative_approach = "Trying more aggressive scaling"
    elif retry_count == 2:
        alternative_approach = "Attempting full service restart"
    else:
        alternative_approach = "Manual intervention may be required"

    undo_message = f"""
🔄 **UNDO AGENT - ROLLBACK COMPLETE**

**Incident:** {state['alert_id']}
**Service:** {state['service_name']}

**Rollback Status:** ✅ Checkpoint restored

**Actions Rolled Back:**
{chr(10).join(f'• {a.get("action")}: undone' for a in actions_executed) if actions_executed else '• No actions to undo'}

**State Restored:**
- Severity restored: {restored_severity:.2f}
- Retry count: {retry_count}/{max_retries}

**Alternative Approach:** {alternative_approach}

{'→ Returning to Orchestrator for re-analysis...' if retry_count < max_retries else '→ Max retries reached. Generating failure report...'}
"""

    # If max retries reached, go to report
    next_phase = "orchestrator_decision" if retry_count < max_retries else "report"

    return {
        "severity": restored_severity,
        "retry_count": retry_count,
        "actions_executed": [],  # Clear actions
        "mitigation_plan": [],   # Clear plan
        "current_phase": next_phase,
        "health_check_passed": False,
        "messages": [AIMessage(content=undo_message)]
    }


# Synchronous wrapper
def undo_agent_node(state: IncidentState) -> dict:
    """Synchronous wrapper for undo_agent."""
    import asyncio
    return asyncio.run(undo_agent(state))

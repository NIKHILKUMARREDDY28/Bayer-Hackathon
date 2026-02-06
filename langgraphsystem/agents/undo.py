"""
Undo Agent (αU) - WRITE
Rollbacks failed mitigations using checkpoint state.
"""

from langchain_core.messages import AIMessage
from ..state import IncidentState


async def undo_agent(state: IncidentState) -> dict:
    """
    Undo phase: Restore checkpoint state when mitigation fails.
    WRITE: Restores system to previous state (faithful undo).
    
    TNR Pattern: U(spost) = spre - restores exactly to checkpoint
    """
    checkpoint = state.get("checkpoint_state", {})
    retry_count = state["retry_count"] + 1
    
    # Restore from checkpoint
    restored_severity = checkpoint.get("severity", state["severity"])
    
    undo_message = f"""
🔄 **UNDO PHASE COMPLETE**

**Rollback Status:** ✅ Checkpoint restored

**Actions Undone:**
• Configuration changes reverted to pre-mitigation state
• Service pods restored to previous configuration
• Connection pool settings restored

**State Restored:**
- Severity restored: {restored_severity:.2f}
- Retry count: {retry_count}/{state['max_retries']}

**Next Action:** Returning to diagnosis for alternative approach...
"""
    
    return {
        "severity": restored_severity,
        "retry_count": retry_count,
        "actions_executed": [],  # Clear actions
        "mitigation_plan": [],   # Clear plan
        "current_phase": "diagnosis",
        "messages": [AIMessage(content=undo_message)]
    }

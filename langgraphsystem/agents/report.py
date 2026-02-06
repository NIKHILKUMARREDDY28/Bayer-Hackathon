"""
Report Agent - Final RCA Generation
Generates comprehensive Root Cause Analysis markdown report.
Called by Orchestrator after successful mitigation.
Uses OpenAI as the brain for intelligent report generation.
"""

from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..state import IncidentState

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

REPORT_SYSTEM_PROMPT = """You are an expert SRE Report Generation Agent for the Autonomous Incident Commander.
Your role is to create comprehensive Root Cause Analysis (RCA) reports.

REPORT STRUCTURE:
1. Executive Summary (2-3 sentences for leadership)
2. Incident Timeline
3. Root Cause Analysis
4. Impact Assessment
5. Mitigation Actions Taken
6. Lessons Learned
7. Recommendations for Prevention

TONE:
- Professional and objective
- Data-driven with specific metrics
- Actionable recommendations
- Suitable for stakeholder review

Generate a well-structured RCA report based on the incident data."""


async def report_agent(state: IncidentState) -> dict:
    """
    Report phase: Generate comprehensive RCA report.
    Final node in the workflow.
    """
    alert_id = state["alert_id"]
    service_name = state["service_name"]
    root_cause = state.get("root_cause") or "Unknown"
    severity = state.get("severity", 0)
    initial_severity = (state.get("checkpoint_state") or {}).get("severity", 1.0)

    # Gather all analysis (ensure dict, not None)
    logs_analysis = state.get("logs_analysis") or {}
    metrics_analysis = state.get("metrics_analysis") or {}
    deployment_analysis = state.get("deployment_analysis") or {}
    mitigation_plan = state.get("mitigation_plan") or []
    actions_executed = state.get("actions_executed") or []
    health_passed = state.get("health_check_passed", False)
    orchestrator_reasoning = state.get("orchestrator_reasoning") or ""

    # Prepare context for LLM report generation
    report_context = f"""
Generate an RCA report for the following incident:

INCIDENT DETAILS:
- Alert ID: {alert_id}
- Service: {service_name}
- Status: {'RESOLVED' if health_passed else 'REQUIRES ATTENTION'}
- Initial Severity: {initial_severity:.2f}/1.0
- Final Severity: {severity:.2f}/1.0
- Improvement: {((initial_severity - severity) / initial_severity * 100):.1f}%

ROOT CAUSE: {root_cause}

LOGS ANALYSIS:
- Anomaly Type: {state.get('anomaly_type', 'N/A')}
- Summary: {logs_analysis.get('summary', 'N/A')}
- Error Count: {logs_analysis.get('error_count', 'N/A')}

METRICS ANALYSIS (PROMETHEUS):
- Anomaly Category: {metrics_analysis.get('anomaly_category', 'N/A')}
- Critical Metrics: {metrics_analysis.get('critical_metrics', [])}
- Correlation: {metrics_analysis.get('correlation_with_logs', 'N/A')}

DEPLOYMENT ANALYSIS:
- Correlated Deployment: {deployment_analysis.get('correlated_deployment_id', 'N/A')}
- Evidence: {deployment_analysis.get('correlation_evidence', 'N/A')}
- Rollback Performed: {deployment_analysis.get('rollback_recommended', False)}

ORCHESTRATOR REASONING: {orchestrator_reasoning}

MITIGATION ACTIONS:
{chr(10).join(f'- {step}' for step in mitigation_plan) if mitigation_plan else 'N/A'}

ACTIONS EXECUTED:
{chr(10).join(f'- {a.get("action")}: {a.get("status")} - {a.get("details")}' for a in actions_executed) if actions_executed else 'N/A'}

Generate a comprehensive RCA report.
"""

    # Use LLM for report generation
    messages = [
        SystemMessage(content=REPORT_SYSTEM_PROMPT),
        HumanMessage(content=report_context)
    ]

    response = await llm.ainvoke(messages)
    llm_rca_analysis = response.content

    # Generate structured RCA markdown
    rca_report = f"""
# Root Cause Analysis Report

## Incident Summary
| Field | Value |
|-------|-------|
| **Alert ID** | {alert_id} |
| **Service** | {service_name} |
| **Status** | {'✅ RESOLVED' if health_passed else '⚠️ REQUIRES ATTENTION'} |
| **Generated** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Severity Timeline
- **Initial Severity:** {initial_severity:.2f}/1.0
- **Final Severity:** {severity:.2f}/1.0
- **Improvement:** {((initial_severity - severity) / initial_severity * 100):.1f}%

## Root Cause
{root_cause}

## Multi-Agent Analysis Summary

### Logs Agent Findings
- Anomaly Type: {state.get('anomaly_type', 'N/A')}
- Summary: {logs_analysis.get('summary', 'N/A')}
- Error Count: {logs_analysis.get('error_count', 0)}
- Critical Patterns: {', '.join(logs_analysis.get('critical_patterns', [])) or 'None'}

### Metrics Agent (Prometheus) Findings
- Anomaly Category: {metrics_analysis.get('anomaly_category', 'N/A')}
- Critical Metrics: {', '.join(metrics_analysis.get('critical_metrics', [])) or 'None'}
- Warning Metrics: {', '.join(metrics_analysis.get('warning_metrics', [])) or 'None'}
- Hypothesis: {metrics_analysis.get('root_cause_hypothesis', 'N/A')}

### Deployment Agent Findings
- Correlated: {'Yes' if deployment_analysis.get('deployment_correlated') else 'No'}
- Suspect Deployment: {deployment_analysis.get('correlated_deployment_id', 'N/A')}
- Type: {deployment_analysis.get('deployment_type', 'N/A')}
- Evidence: {deployment_analysis.get('correlation_evidence', 'N/A')}

## Orchestrator Decision Path
{orchestrator_reasoning or 'Standard workflow executed'}

## Mitigation Actions
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(mitigation_plan)) if mitigation_plan else 'No mitigation performed'}

## Actions Executed
| Action | Status | Details |
|--------|--------|---------|
{chr(10).join(f"| {a['action']} | {a['status']} | {a['details']} |" for a in actions_executed) if actions_executed else '| N/A | N/A | N/A |'}

## AI-Generated Analysis
{llm_rca_analysis}

## Recommendations
1. **Immediate:** {'No further action required' if health_passed else 'Manual investigation recommended'}
2. **Short-term:** Implement additional monitoring and alerting
3. **Long-term:** Review configuration change processes and implement canary deployments

---
*Report generated by Autonomous Incident Commander with multi-agent AI assistance*
*Agents involved: Logs Agent, Metrics Agent (Prometheus), Deployment Agent, Orchestrator, Mitigation Agent*
"""
    
    report_message = f"""
📝 **RCA REPORT GENERATED**

**Incident:** {alert_id}
**Service:** {service_name}
**Status:** {'✅ Resolved' if health_passed else '⚠️ Requires Review'}
**Severity:** {initial_severity:.2f} → {severity:.2f} ({((initial_severity - severity) / initial_severity * 100):.1f}% improvement)

**Multi-Agent Analysis:**
- Logs Agent: {'✅ Completed' if logs_analysis else '⏭️ Skipped'}
- Metrics Agent: {'✅ Completed' if metrics_analysis else '⏭️ Skipped'}
- Deployment Agent: {'✅ Completed' if deployment_analysis else '⏭️ Skipped'}

**Root Cause:** {root_cause}

The full RCA report has been generated and saved.
"""
    
    return {
        "rca_report": rca_report,
        "current_phase": "complete",
        "health_check_passed": health_passed,
        "messages": [AIMessage(content=report_message)]
    }


# Synchronous wrapper
def report_agent_node(state: IncidentState) -> dict:
    """Synchronous wrapper for report_agent."""
    import asyncio
    return asyncio.run(report_agent(state))

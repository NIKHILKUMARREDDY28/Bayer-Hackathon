"""
Deployment Agent - Analyzes CI/CD history and configuration changes.
Called by Orchestrator when deployment correlation is needed.
Uses OpenAI as the brain for intelligent deployment analysis.
"""

import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..state import IncidentState
from ..tools.deployments import get_recent_deployments, get_deployment_diff, recommend_rollback


# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
)

DEPLOYMENT_ANALYSIS_SYSTEM_PROMPT = """You are an expert DevOps/SRE Deployment Analysis Agent for the Autonomous Incident Commander.
Your role is to correlate incidents with recent deployments and configuration changes.

TASK:
Analyze the deployment history and identify if a recent change caused the incident.

DEPLOYMENT TYPES TO CHECK:
- CONFIG_CHANGE: Configuration modifications (connection pools, timeouts, feature flags)
- CODE_DEPLOY: Application code deployments
- INFRA_CHANGE: Infrastructure changes (scaling, networking)
- DEPENDENCY_UPDATE: Library or dependency updates

CORRELATION PATTERNS:
- Temporal correlation: Deployment just before incident onset
- Latent bugs: Deployment earlier but issue manifests under load
- Configuration drift: Gradual degradation after config change
- Rollback candidate: Clear correlation with recent deployment

OUTPUT FORMAT (Strict JSON):
{{
    "deployment_correlated": true/false,
    "correlated_deployment_id": "ID of the suspect deployment or null",
    "deployment_type": "CONFIG_CHANGE/CODE_DEPLOY/INFRA_CHANGE/DEPENDENCY_UPDATE or null",
    "correlation_evidence": "Specific evidence linking deployment to incident",
    "time_correlation": {{
        "deployment_time": "timestamp",
        "incident_onset": "estimated timestamp",
        "time_gap_minutes": number
    }},
    "is_latent_bug": true/false,
    "rollback_recommended": true/false,
    "rollback_target": "Version or config to rollback to",
    "confidence_score": 0-100,
    "alternative_causes": ["List of other possible causes if deployment not correlated"]
}}

Be thorough in timeline analysis. Look for the 'smoking gun'."""


async def deployment_agent(state: IncidentState) -> Dict[str, Any]:
    """
    Deployment Agent: Analyzes CI/CD history and config changes.
    Called by Orchestrator when deployment correlation is needed.
    """
    service_name = state["service_name"]
    alert_type = state["alert_type"]
    alert_id = state["alert_id"]
    logs_analysis = state.get("logs_analysis") or {}
    metrics_analysis = state.get("metrics_analysis") or {}
    anomaly_type = state.get("anomaly_type") or "unknown"

    # Get deployment history - either from state or mock data
    deployments = state.get("deployment_history", [])
    if not deployments:
        deployments = get_recent_deployments(service_name)

    # Get rollback recommendation
    rollback_rec = recommend_rollback(deployments)

    # Format deployments for analysis
    deployments_text = ""
    for d in deployments:
        deployments_text += f"""
Deployment ID: {d.get('id')}
- Time: {d.get('timestamp')}
- Type: {d.get('type')}
- Service: {d.get('service')}
- Description: {d.get('description')}
- Has Config Change: {d.get('has_config_change')}
- Change Type: {d.get('change_type', 'N/A')}
- Author: {d.get('author')}
"""

    # Prepare context for LLM
    analysis_context = f"""
Analyze the deployment history for service: {service_name}
Alert ID: {alert_id}

INCIDENT CONTEXT:
- Alert Type: {alert_type}
- Anomaly Type: {anomaly_type}
- Log Analysis: {logs_analysis.get('summary', 'N/A')}
- Metrics Analysis: {metrics_analysis.get('root_cause_hypothesis', 'N/A')}

RECENT DEPLOYMENTS:
{deployments_text}

ROLLBACK RECOMMENDATION FROM SYSTEM:
- Recommend Rollback: {rollback_rec.get('recommend_rollback')}
- Target: {rollback_rec.get('target_deployment', 'N/A')}
- Reason: {rollback_rec.get('reason', 'N/A')}

Correlate the incident with deployment history. Identify the 'smoking gun'.
"""

    # Build the chain
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", DEPLOYMENT_ANALYSIS_SYSTEM_PROMPT),
            ("human", "{context}"),
        ]
    )

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    # Invoke LLM for analysis
    try:
        result = chain.invoke({"context": analysis_context})
    except Exception as e:
        # Fallback if JSON parsing fails
        result = {
            "deployment_correlated": rollback_rec.get("recommend_rollback", False),
            "correlated_deployment_id": rollback_rec.get("target_deployment"),
            "deployment_type": "CONFIG_CHANGE" if rollback_rec.get("recommend_rollback") else None,
            "correlation_evidence": f"Error during analysis: {str(e)}. Using system recommendation.",
            "time_correlation": {
                "deployment_time": "unknown",
                "incident_onset": "unknown",
                "time_gap_minutes": 0,
            },
            "is_latent_bug": False,
            "rollback_recommended": rollback_rec.get("recommend_rollback", False),
            "rollback_target": rollback_rec.get("target_deployment"),
            "confidence_score": 50,
            "alternative_causes": [],
        }

    # Build response message
    deployment_message = f"""
🚀 **DEPLOYMENT AGENT ANALYSIS COMPLETE**

**Service:** {service_name}
**Alert ID:** {alert_id}

**Deployment Correlation:**
- Correlated: {'✅ YES' if result.get('deployment_correlated') else '❌ NO'}
- Suspect Deployment: {result.get('correlated_deployment_id', 'N/A')}
- Deployment Type: {result.get('deployment_type', 'N/A')}

**Timeline Analysis:**
- Deployment Time: {result.get('time_correlation', {}).get('deployment_time', 'N/A')}
- Incident Onset: {result.get('time_correlation', {}).get('incident_onset', 'N/A')}
- Time Gap: {result.get('time_correlation', {}).get('time_gap_minutes', 'N/A')} minutes

**Evidence:**
{result.get('correlation_evidence', 'N/A')}

**Is Latent Bug:** {'Yes' if result.get('is_latent_bug') else 'No'}

**Rollback Recommendation:**
- Recommended: {'✅ YES' if result.get('rollback_recommended') else '❌ NO'}
- Target: {result.get('rollback_target', 'N/A')}
- Confidence: {result.get('confidence_score', 0)}%

**Alternative Causes:**
{chr(10).join(f'• {c}' for c in result.get('alternative_causes', [])) or '• None identified'}

→ Handing off to Orchestrator for final decision...
"""

    return {
        "deployment_analysis": result,
        "deployment_correlated": result.get("deployment_correlated", False),
        "current_phase": "orchestrator_decision",
        "messages": [AIMessage(content=deployment_message)],
    }


# Synchronous wrapper for the graph
def deployment_agent_node(state: IncidentState) -> Dict[str, Any]:
    """Synchronous wrapper for deployment_agent."""
    import asyncio

    return asyncio.run(deployment_agent(state))

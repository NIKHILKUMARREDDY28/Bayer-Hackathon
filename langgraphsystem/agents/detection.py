"""
Detection Agent (αD) - READ-only
Identifies failures from incoming alerts and establishes initial error state.
Uses OpenAI as the brain for intelligent analysis.
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state import IncidentState

# Initialize OpenAI LLM
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
)

DETECTION_SYSTEM_PROMPT = """You are an expert SRE (Site Reliability Engineer) detection agent.
Your role is to analyze incoming alerts and identify potential issues.

Given an alert, you must:
1. Identify the type and severity of the issue
2. List all detected problems
3. Assess the potential impact on the system
4. Provide initial observations for the diagnosis phase

Be concise but thorough. Focus on actionable insights."""


async def detection_agent(state: IncidentState) -> dict:
    """
    Detection phase: Analyze incoming alert and identify issues using OpenAI.
    READ-only: Does not mutate system state.
    """
    alert_id = state["alert_id"]
    alert_type = state["alert_type"]
    severity = state["severity"]
    service_name = state["service_name"]
    
    # Prepare context for LLM
    alert_context = f"""
Analyze the following alert:

Alert ID: {alert_id}
Alert Type: {alert_type}
Severity: {severity:.2f}/1.0 (where 1.0 is critical)
Service Name: {service_name}

Please provide:
1. A list of detected issues (be specific)
2. Potential impact assessment
3. Initial observations for diagnosis
"""

    # Use OpenAI for intelligent detection
    messages = [
        SystemMessage(content=DETECTION_SYSTEM_PROMPT),
        HumanMessage(content=alert_context)
    ]

    response = await llm.ainvoke(messages)
    llm_analysis = response.content

    # Extract detected issues based on alert type and LLM analysis
    detected_issues = []
    
    if alert_type == "latency_spike":
        detected_issues.append(f"High latency detected in {service_name}")
        detected_issues.append(f"Severity level: {severity:.2f}")
        detected_issues.append("Potential service degradation in progress")
        
    elif alert_type == "error_rate":
        detected_issues.append(f"Elevated error rate in {service_name}")
        detected_issues.append("Error threshold exceeded")

    elif alert_type == "cpu_spike":
        detected_issues.append(f"CPU utilization spike in {service_name}")
        detected_issues.append("Resource exhaustion risk detected")
        
    elif alert_type == "db_connection":
        detected_issues.append(f"Database connection pool exhausted for {service_name}")
        detected_issues.append("Connection timeout errors detected")
    
    else:
        detected_issues.append(f"Unknown alert type: {alert_type}")
        detected_issues.append(f"Service affected: {service_name}")
    
    # Create detection message with LLM analysis
    detection_summary = f"""
🔍 **DETECTION PHASE COMPLETE**

**Alert ID:** {alert_id}
**Service:** {service_name}
**Severity:** {severity:.2f}/1.0
**Alert Type:** {alert_type}

**Detected Issues:**
{chr(10).join(f'• {issue}' for issue in detected_issues)}

**AI Analysis:**
{llm_analysis}

Proceeding to diagnosis phase...
"""
    
    return {
        "detected_issues": detected_issues,
        "current_phase": "diagnosis",
        "messages": [AIMessage(content=detection_summary)]
    }

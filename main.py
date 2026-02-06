"""
Main orchestrator for Autonomous Incident Commander.
Runs the LangGraph incident response workflow with mock events.
Uses Orchestrator-based coordination pattern.
"""

# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any

from langgraphsystem.graph import incident_graph
from langgraphsystem.state import create_initial_state, IncidentState
from langgraphsystem.tools.logs import get_mock_logs
from langgraphsystem.tools.prometheus import get_mock_metrics
from langgraphsystem.tools.deployments import get_recent_deployments


# Mock events for testing different incident scenarios
MOCK_EVENTS: List[Dict[str, Any]] = [
    {
        "alert_id": f"ALT-{uuid.uuid4().hex[:8]}",
        "alert_type": "latency_spike",
        "severity": 0.85,
        "service_name": "checkout-service",
        "description": "High latency detected in checkout service - p99 > 2000ms"
    },
    {
        "alert_id": f"ALT-{uuid.uuid4().hex[:8]}",
        "alert_type": "error_rate",
        "severity": 0.75,
        "service_name": "payment-service",
        "description": "Elevated error rate in payment service - 15% errors"
    },
    {
        "alert_id": f"ALT-{uuid.uuid4().hex[:8]}",
        "alert_type": "cpu_spike",
        "severity": 0.90,
        "service_name": "compute-service",
        "description": "CPU utilization spike detected - 95% usage"
    },
    {
        "alert_id": f"ALT-{uuid.uuid4().hex[:8]}",
        "alert_type": "db_connection",
        "severity": 0.95,
        "service_name": "db-proxy",
        "description": "Database connection pool exhausted"
    },
]


async def run_incident_workflow(event: Dict[str, Any], thread_id: str = None) -> Dict[str, Any]:
    """
    Run the incident response workflow for a single event.

    Workflow:
    1. Logs Agent analyzes logs for anomalies
    2. Orchestrator decides to call Metrics Agent (Prometheus) if anomaly detected
    3. Orchestrator decides to call Deployment Agent if needed
    4. Orchestrator triggers Mitigation when root cause is identified
    5. Report Agent generates RCA

    Args:
        event: Alert event containing alert_id, alert_type, severity, service_name
        thread_id: Optional thread ID for state persistence

    Returns:
        Final state after workflow completion
    """
    print(f"\n{'='*80}")
    print(f"🚨 INCIDENT DETECTED: {event['alert_id']}")
    print(f"   Service: {event['service_name']}")
    print(f"   Type: {event['alert_type']}")
    print(f"   Severity: {event['severity']:.2f}")
    print(f"   Description: {event.get('description', 'N/A')}")
    print(f"{'='*80}")

    # Get mock data for the incident
    raw_logs = get_mock_logs(event['service_name'], event['alert_type'])
    raw_metrics = get_mock_metrics(event['service_name'], event['alert_type'])
    deployment_history = get_recent_deployments(event['service_name'])

    # Create initial state with all mock data
    initial_state = create_initial_state(
        alert_id=event["alert_id"],
        alert_type=event["alert_type"],
        severity=event["severity"],
        service_name=event["service_name"],
        raw_logs=raw_logs,
        raw_metrics=raw_metrics,
        deployment_history=deployment_history
    )

    # Create unique thread ID for this incident
    if thread_id is None:
        thread_id = f"incident-{event['alert_id']}"

    config = {"configurable": {"thread_id": thread_id}}

    # Run the graph and accumulate state
    accumulated_state = {}
    try:
        async for event_output in incident_graph.astream(initial_state, config):
            # Print each node's output
            for node_name, node_output in event_output.items():
                print(f"\n--- {node_name.upper()} ---")
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        print(msg.content)
                # Accumulate state from all nodes
                accumulated_state.update(node_output)
    except Exception as e:
        print(f"❌ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        raise

    return accumulated_state


async def run_all_incidents():
    """Run all mock incidents through the orchestrator-based workflow."""
    print("\n" + "="*80)
    print("🤖 AUTONOMOUS INCIDENT COMMANDER - ORCHESTRATOR MODE")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Total incidents to process: {len(MOCK_EVENTS)}")
    print("="*80)
    print("\n📋 Workflow: Logs Agent → Orchestrator → Metrics Agent → Orchestrator → ")
    print("             Deployment Agent → Orchestrator → Mitigation → Report")

    results = []

    for i, event in enumerate(MOCK_EVENTS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# Processing incident {i}/{len(MOCK_EVENTS)}")
        print(f"{'#'*80}")

        try:
            result = await run_incident_workflow(event)
            results.append({
                "alert_id": event["alert_id"],
                "service": event["service_name"],
                "status": "completed",
                "health_check_passed": result.get("health_check_passed", False) if result else False,
                "root_cause": result.get("root_cause", "Unknown"),
            })
        except Exception as e:
            results.append({
                "alert_id": event["alert_id"],
                "service": event["service_name"],
                "status": "failed",
                "error": str(e)
            })

    # Print summary
    print("\n\n" + "="*80)
    print("📊 BATCH PROCESSING SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r["status"] == "completed")
    resolved = sum(1 for r in results if r.get("health_check_passed", False))

    print(f"\nTotal Incidents: {len(results)}")
    print(f"Successfully Processed: {successful}")
    print(f"Incidents Resolved: {resolved}")
    print(f"Failed Processing: {len(results) - successful}")

    print("\nDetailed Results:")
    for r in results:
        status_icon = "✅" if r.get("health_check_passed") else "⚠️" if r["status"] == "completed" else "❌"
        root_cause = r.get("root_cause", "N/A")[:50] + "..." if len(r.get("root_cause", "")) > 50 else r.get("root_cause", "N/A")
        print(f"  {status_icon} {r['alert_id']} ({r['service']})")
        print(f"      Status: {r['status']}")
        if r.get("root_cause"):
            print(f"      Root Cause: {root_cause}")

    return results


async def run_single_incident(alert_type: str = "latency_spike"):
    """Run a single incident for quick testing."""
    event = next((e for e in MOCK_EVENTS if e["alert_type"] == alert_type), MOCK_EVENTS[0])
    return await run_incident_workflow(event)


def main():
    """Main entry point."""
    print("\n🚀 Starting Autonomous Incident Commander...")
    print("   Framework: LangGraph with Orchestrator Pattern")
    print("   Mode: Multi-Agent Coordination")
    print("\n   Agent Flow:")
    print("   1. Logs Agent - Analyzes logs for anomalies")
    print("   2. Orchestrator - Decides next action")
    print("   3. Metrics Agent - Prometheus metrics analysis (if needed)")
    print("   4. Deployment Agent - CI/CD correlation (if needed)")
    print("   5. Mitigation Agent - Executes remediation")
    print("   6. Report Agent - Generates RCA\n")

    # Run all incidents
    asyncio.run(run_all_incidents())


if __name__ == "__main__":
    main()

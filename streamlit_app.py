"""
Streamlit Testing Interface for Autonomous Incident Commander.
Interactive dashboard for triggering and visualizing incident response.
"""

import streamlit as st
import asyncio
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Autonomous Incident Commander",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00D4FF;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #00D4FF;
    }
    .severity-high { color: #ff4444; }
    .severity-medium { color: #ffaa00; }
    .severity-low { color: #44ff44; }
    .phase-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .stExpander {
        background-color: #1a1a2e;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


def run_async(coro):
    """Helper to run async code in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def run_incident_graph(initial_state):
    """Run the incident graph asynchronously."""
    from langgraphsystem.graph import incident_graph
    
    config = {"configurable": {"thread_id": f"incident-{datetime.now().timestamp()}"}}
    
    # Stream results
    results = []
    async for event in incident_graph.astream(initial_state, config):
        results.append(event)
    
    return results


def main():
    # Header
    st.markdown('<div class="main-header">🚨 Autonomous Incident Commander</div>', unsafe_allow_html=True)
    st.markdown("### Multi-Agent AIOps System | Bayer AI Hackathon 2026")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Demo Scenarios")
        scenario = st.selectbox(
            "Select Scenario",
            [
                "Latent Configuration Bug",
                "Database Connection Exhaustion", 
                "High Error Rate",
                "CPU Resource Spike"
            ]
        )
        
        st.subheader("Alert Settings")
        service_name = st.text_input("Service Name", value="checkout-service")
        
        severity = st.slider("Initial Severity", 0.0, 1.0, 0.85, 0.05)
        
        st.subheader("Agent Settings")
        max_retries = st.number_input("Max Retries", min_value=1, max_value=5, value=3)
        
        st.divider()
        
        run_button = st.button("🚀 Trigger Incident", type="primary", use_container_width=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Agent Chain of Thought")
        
        # Placeholder for agent outputs
        agent_output = st.container()
        
    with col2:
        st.header("📈 Metrics")
        
        # Metrics display
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Severity", f"{severity:.2f}", delta=None)
        with metric_col2:
            st.metric("Status", "Ready" if not run_button else "Running")
        
        st.header("🔗 Quick Links")
        st.markdown("""
        - [Architecture Diagram](./architecture)
        - [STRATUS Paper](https://arxiv.org/abs/2506.02009)
        - [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
        """)
    
    # Run incident response
    if run_button:
        # Map scenario to alert type
        alert_type_map = {
            "Latent Configuration Bug": "latency_spike",
            "Database Connection Exhaustion": "db_connection",
            "High Error Rate": "error_rate",
            "CPU Resource Spike": "cpu_spike"
        }
        
        alert_type = alert_type_map.get(scenario, "latency_spike")
        
        from langgraphsystem.state import create_initial_state
        
        initial_state = create_initial_state(
            alert_id=f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            alert_type=alert_type,
            severity=severity,
            service_name=service_name
        )
        initial_state["max_retries"] = max_retries
        
        with agent_output:
            st.info(f"🚨 **Incident Triggered:** {scenario}")
            
            # Progress indicator
            progress = st.progress(0)
            status = st.empty()
            
            phases = ["Detection", "Diagnosis", "Mitigation", "Validation", "Report"]
            
            try:
                results = run_async(run_incident_graph(initial_state))
                
                for i, result in enumerate(results):
                    progress.progress((i + 1) / len(phases))
                    
                    for node_name, node_output in result.items():
                        status.text(f"Running: {node_name.capitalize()} Agent...")
                        
                        with st.expander(f"📍 {node_name.upper()} Agent", expanded=True):
                            # Display messages from this node
                            if "messages" in node_output:
                                for msg in node_output["messages"]:
                                    st.markdown(msg.content)
                            
                            # Display key state changes
                            if node_name == "mitigation":
                                health_status = "✅ PASSED" if node_output.get("health_check_passed") else "❌ FAILED"
                                st.metric("Health Check", health_status)
                            
                            if node_name == "report" and "rca_report" in node_output:
                                st.divider()
                                st.subheader("📄 RCA Report")
                                st.markdown(node_output["rca_report"])
                
                progress.progress(1.0)
                status.success("✅ Incident Response Complete!")
                
            except Exception as e:
                st.error(f"Error during execution: {str(e)}")
                st.exception(e)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #888;">
        <p>Autonomous Incident Commander | Bayer AI Hackathon 2026</p>
        <p>Built with LangGraph, Streamlit, and ❤️</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

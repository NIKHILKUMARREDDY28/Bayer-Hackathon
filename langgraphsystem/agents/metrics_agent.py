import os
import json
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain


# --- NEW: LangChain Summarization Logic ---
def summarize_telemetry(raw_data: List[Dict], model: ChatOpenAI) -> str:
    """
    Handles large/variable log inputs by using LangChain's summarization
    capabilities to condense telemetry before reasoning.
    """
    if not raw_data:
        return "No telemetry data available."

    # 1. Convert JSON objects into readable strings (Documents)
    # We focus on the high-signal parts of the JSON
    docs = []
    for entry in raw_data:
        content = (
            f"Time: {entry.get('timestamp')} | "
            f"Alert: {entry.get('alert', {}).get('Trigger')} | "
            f"Metrics: {entry.get('metrics', {}).get('MetricData')} | "
            f"Log: {entry.get('log_record', {}).get('message')}"
        )
        docs.append(Document(page_content=content))

    # 2. Decide strategy based on data size
    # If the log history is short, just use 'stuff' (send all at once)
    # If long, 'map_reduce' or 'refine' is safer for context limits.
    combine_prompt = """
    Summarize the following SRE telemetry logs.
    Focus on:
    1. The timeline of any latency spikes or memory increases.
    2. Any 'FATAL' or 'ERROR' messages.
    3. The frequency of ALARM vs OK statuses.
    TELEMETRY DATA:
    {text}
    CONCISE SRE SUMMARY:"""

    PROMPT = ChatPromptTemplate.from_template(combine_prompt)

    # Use 'map_reduce' to handle very large logs by summarizing chunks first
    chain = load_summarize_chain(
        llm=model, chain_type="map_reduce", combine_prompt=PROMPT, verbose=False
    )

    summary = chain.run(docs)
    return summary


class MetricsAgent:
    def __init__(self, model):
        self.model = model
        self.parser = JsonOutputParser()

        self.system_prompt = """
        You are the 'Metrics Agent' for Bayer's Autonomous Incident Commander.
        Expertise: SRE, CloudWatch Telemetry, and Anomaly Detection.

        TASK:
        Analyze the provided Technical Summary of system telemetry to identify failures.
        ROOT CAUSE CATEGORIES:
        - Memory Leak: Increasing memory trend nearing 100%.
        - Latency Spike: Duration values exceeding 2000ms.
        - OOM (Out of Memory): Fatal exit errors.

        DECISION LOGIC:
        - If the summary indicates a spike but the cause is unclear, set 'needs_logs' to true.
        - If the summary explicitly mentions a 'FATAL' error or 'OOM', set 'needs_logs' to false.

        OUTPUT FORMAT (Strict JSON):
        {{
            "analysis_report": "Summary of the incident timeline and impact.",
            "root_cause": "The suspected primary failure point.",
            "needs_logs": true/false,
            "proposed_remediation": "The fix (e.g., Increase Lambda memory, Scale up, or Rollback).",
            "confidence_score": 0-100
        }}
        """

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n[Metrics Agent] Summarizing and analyzing telemetry...")

        # 1. Pull data from state
        raw_data = state.get("raw_data", [])
        incident_trigger = state.get("incident_trigger", "Unspecified Alert")

        # 2. PERFORM SUMMARIZATION (Handles context limits & variations)
        # We use the same model for summarization, or could use a cheaper one like gpt-4o-mini
        telemetry_summary = summarize_telemetry(raw_data, self.model)

        # 3. Build LCEL Chain for Reasoning
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("human", "Trigger: {trigger}\n\nTechnical Summary of Telemetry:\n{summary}"),
            ]
        )

        chain = prompt | self.model | self.parser

        # 4. Invoke LLM for Final Analysis
        result = chain.invoke({"trigger": incident_trigger, "summary": telemetry_summary})

        # 5. Determine the next node for the Orchestrator
        next_step = "logs_agent" if result["needs_logs"] else "decision_agent"

        report_summary = (
            f"ANALYSIS: {result['analysis_report']}\n"
            f"SUSPECTED ROOT CAUSE: {result['root_cause']}"
        )

        return {
            "metrics_report": report_summary,
            "proposed_solution": result["proposed_remediation"],
            "messages": [AIMessage(content=report_summary)],
            "next_step": next_step,
        }


# --- THE NODE FUNCTION ---
def metrics_node(state: Dict[str, Any]):
    """
    Wrapper for the LangGraph Orchestrator.
    """
    if "llm" not in state or state["llm"] is None:
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
    else:
        llm = state["llm"]

    agent = MetricsAgent(model=llm)
    return agent.run(state)

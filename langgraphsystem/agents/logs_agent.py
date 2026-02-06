import json
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LOGS_SYSTEM_PROMPT = """
You are a production SRE Logs Analysis Agent.

Analyze logs and detect incidents.

Return STRICT JSON with:
- incident_detected (boolean)
- signal_type (memory_leak | db_timeout | exception_spike | isolated_errors | no_incident)
- error_count (integer)
- first_seen (timestamp or null)
- last_seen (timestamp or null)
- summary (short sentence)

ONLY return JSON. No extra text.
"""


def analyze_logs_with_llm(log_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": LOGS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Logs:\n{log_text}"}
        ],
    )

    content = response.choices[0].message.content
    return json.loads(content)
    
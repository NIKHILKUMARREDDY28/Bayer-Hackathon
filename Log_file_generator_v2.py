import json
import os
import random
import uuid
from datetime import datetime, timedelta

# Configuration
DAYS = 15
FILE_NAME = "aws_responder_clean_format.json"
DOWNLOAD_PATH = os.path.expanduser("~/Downloads/")

def generate_aws_ids():
    """Generates professional AWS Trace and Request IDs."""
    trace_id = f"1-{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:24]}"
    request_id = str(uuid.uuid4())
    return trace_id, request_id

def create_log_entry(event_type, ts_iso, req_id, trace_id):
    """Refined log format without @ prefixes and random noise."""
    
    # Standard health message
    message = f"INFO: Request processed successfully. Status: 200. TraceId: {trace_id}"
    
    # Failure Logic - Specific Signatures
    if event_type == "memory_exceeding":
        message = (f"REPORT RequestId: {req_id} Duration: 45.10 ms Billed Duration: 100 ms "
                   f"Memory Size: 128 MB Max Memory Used: 129 MB\n"
                   f"FATAL: Runtime.ExitError - Out of Memory (OOM) at task execution.")
        
    elif event_type == "p99_latency_spike":
        message = (f"WARN: Latency threshold breached. Request duration: 5240ms. "
                   f"Downstream service 'PaymentGateway' responded in 5100ms. RequestId: {req_id}")
        
    elif event_type == "memory_leak":
        message = (f"ERROR: Resource leak detected in process heap. "
                   f"Current usage: 498MB / 512MB. Trend: Increasing. TraceId: {trace_id}")
        
    elif event_type == "deployment_issue":
        message = (f"CRITICAL: Deployment rollback initiated. ID: d-A1B2C3D4E. "
                   f"Reason: ELB HealthCheck failed for instance: i-0876543210")

    return {
        "timestamp": ts_iso,
        "ingestionTime": datetime.utcnow().isoformat() + "Z",
        "logStream": "production-log-stream-001",
        "logGroup": "/aws/lambda/high-velocity-service",
        "message": message,
        "requestId": req_id,
        "xrayTraceId": trace_id
    }

data_points = []
start_time = datetime.utcnow() - timedelta(days=DAYS)

for i in range(DAYS * 24):
    current_dt = start_time + timedelta(hours=i)
    ts_iso = current_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    day = (i // 24) + 1
    trace_id, req_id = generate_aws_ids()
    
    # Scheduled Failures
    event_type = "normal"
    mem_val, lat_val = random.uniform(35, 45), random.uniform(10, 50)

    if day == 2: event_type, mem_val = "memory_leak", 96.5
    elif day == 5: event_type, lat_val = "p99_latency_spike", 5240.0
    elif day == 9: event_type = "deployment_issue"
    elif day == 14: event_type, mem_val = "memory_exceeding", 101.0

    data_points.append({
        "timestamp": ts_iso,
        "log_record": create_log_entry(event_type, ts_iso, req_id, trace_id),
        "metrics": {
            "Namespace": "AWS/Lambda",
            "MetricData": [
                {"MetricName": "Duration", "Value": round(lat_val, 2), "Unit": "Milliseconds"},
                {"MetricName": "MemoryUsage", "Value": round(mem_val, 2), "Unit": "Percent"}
            ]
        },
        "alert": {
            "Source": "CloudWatch/Alarm",
            "Status": "ALARM" if event_type != "normal" else "OK",
            "Trigger": event_type
        }
    })

# Save to file
full_path = os.path.join(DOWNLOAD_PATH, FILE_NAME)
with open(full_path, "w") as f:
    json.dump(data_points, f, indent=4)

print(f"Clean diagnostic dataset saved: {full_path}")
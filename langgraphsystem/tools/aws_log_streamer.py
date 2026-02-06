"""
Mock AWS Log Streaming Service
Streams logs from aws_responder_clean_format.json with alert detection.
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime


class AWSLogStreamer:
    """
    Mock service that simulates AWS CloudWatch log streaming.
    Reads from aws_responder_clean_format.json and streams in chunks.
    """
    
    def __init__(self, log_file: str = None):
        if log_file is None:
            # Default to the aws_responder file in project root
            log_file = Path(__file__).parent.parent / "aws_responder_clean_format.json"
        self.log_file = Path(log_file)
        self._logs: Optional[List[Dict]] = None
    
    def load_logs(self) -> List[Dict]:
        """Load all logs from JSON file."""
        if self._logs is None:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    self._logs = json.load(f)
            else:
                self._logs = []
        return self._logs
    
    def get_alerts(self) -> List[Dict]:
        """Get all log entries with ALARM status."""
        logs = self.load_logs()
        return [
            log for log in logs 
            if log.get('alert', {}).get('Status') == 'ALARM'
        ]
    
    def get_logs_by_trigger(self, trigger: str) -> List[Dict]:
        """Get logs matching a specific alert trigger."""
        logs = self.load_logs()
        return [
            log for log in logs
            if log.get('alert', {}).get('Trigger') == trigger
        ]
    
    def get_recent_logs(self, count: int = 100) -> List[Dict]:
        """Get the most recent N logs."""
        logs = self.load_logs()
        return logs[-count:] if len(logs) > count else logs
    
    def get_error_logs(self) -> List[Dict]:
        """Get all ERROR level logs."""
        logs = self.load_logs()
        return [
            log for log in logs
            if 'ERROR' in log.get('log_record', {}).get('message', '')
        ]
    
    async def stream_logs(
        self, 
        chunk_size: int = 100,
        delay_seconds: float = 0.5
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Stream logs in chunks with configurable delay.
        Simulates real-time log ingestion.
        """
        logs = self.load_logs()
        for i in range(0, len(logs), chunk_size):
            chunk = logs[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(delay_seconds)
    
    def detect_anomalies(self) -> List[Dict]:
        """
        Detect anomalies in the log stream.
        Returns list of alert-triggering events.
        """
        alerts = self.get_alerts()
        anomalies = []
        
        for log in alerts:
            alert = log.get('alert', {})
            metrics = log.get('metrics', {}).get('MetricData', [])
            
            anomaly = {
                'timestamp': log.get('timestamp'),
                'alert_status': alert.get('Status'),
                'trigger': alert.get('Trigger'),
                'log_group': log.get('log_record', {}).get('logGroup'),
                'message': log.get('log_record', {}).get('message'),
                'metrics': {
                    m['MetricName']: m['Value'] 
                    for m in metrics
                },
                'severity': self._calculate_severity(alert, metrics)
            }
            anomalies.append(anomaly)
        
        return anomalies
    
    def _calculate_severity(self, alert: Dict, metrics: List[Dict]) -> float:
        """Calculate severity score (0-1) based on alert and metrics."""
        severity = 0.5  # Base severity for any alert
        
        trigger = alert.get('Trigger', '')
        if trigger == 'memory_leak':
            severity = 0.9
        elif trigger == 'high_latency':
            severity = 0.7
        elif trigger == 'error_rate':
            severity = 0.8
        
        # Adjust based on memory usage
        for m in metrics:
            if m['MetricName'] == 'MemoryUsage' and m['Value'] > 90:
                severity = max(severity, 0.95)
            if m['MetricName'] == 'Duration' and m['Value'] > 1000:
                severity = max(severity, 0.8)
        
        return min(severity, 1.0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the log stream."""
        logs = self.load_logs()
        alerts = self.get_alerts()
        errors = self.get_error_logs()
        
        return {
            'total_logs': len(logs),
            'total_alerts': len(alerts),
            'total_errors': len(errors),
            'alert_triggers': list(set(
                a.get('alert', {}).get('Trigger') 
                for a in alerts
            )),
            'log_groups': list(set(
                l.get('log_record', {}).get('logGroup')
                for l in logs
            )),
            'time_range': {
                'start': logs[0].get('timestamp') if logs else None,
                'end': logs[-1].get('timestamp') if logs else None,
            }
        }


# Singleton instance
_log_streamer: Optional[AWSLogStreamer] = None


def get_log_streamer() -> AWSLogStreamer:
    """Get or create the log streamer singleton."""
    global _log_streamer
    if _log_streamer is None:
        _log_streamer = AWSLogStreamer()
    return _log_streamer


# Convenience functions for agent tools
def get_aws_alerts() -> List[Dict]:
    """Get all AWS alerts from the log stream."""
    return get_log_streamer().get_alerts()


def get_aws_anomalies() -> List[Dict]:
    """Detect and return all anomalies."""
    return get_log_streamer().detect_anomalies()


def get_aws_log_summary() -> Dict:
    """Get summary of the AWS log stream."""
    return get_log_streamer().get_summary()

"""
MCP-Compatible Email Tool using Resend API.

This follows the Model Context Protocol (MCP) pattern for tool integration,
making it compatible with langchain-mcp-adapters for LangGraph agents.

Requires: pip install resend (or add to pyproject.toml)
API Key: Get from https://resend.com/api-keys
"""

import os
import json
from typing import Optional, List, Union, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class MCPEmailTool:
    """
    MCP-compatible email sending tool using Resend API.
    
    This follows the MCP tool specification pattern:
    - name: Tool identifier
    - description: What the tool does
    - inputSchema: JSON Schema for parameters
    - handler: The function that executes the tool
    
    Configure via environment:
    - RESEND_API_KEY: Your Resend API key
    - RESEND_SENDER: Verified sender email (optional)
    """
    
    # MCP Tool Metadata
    name = "send_email"
    description = "Send an email using Resend API. Supports plain text and HTML emails with optional CC, BCC, and reply-to addresses."
    
    input_schema = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address"
            },
            "subject": {
                "type": "string", 
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Plain text email body"
            },
            "html_body": {
                "type": "string",
                "description": "HTML email body (optional)"
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CC recipients (optional)"
            },
            "bcc": {
                "type": "array", 
                "items": {"type": "string"},
                "description": "BCC recipients (optional)"
            },
            "reply_to": {
                "type": "string",
                "description": "Reply-to address (optional)"
            }
        },
        "required": ["to", "subject", "body"]
    }
    
    def __init__(self):
        self.api_key = os.getenv('RESEND_API_KEY', '')
        self.sender = os.getenv('RESEND_SENDER', 'onboarding@resend.dev')
        self.reply_to = os.getenv('RESEND_REPLY_TO', '')
        self._resend = None
    
    @property
    def resend(self):
        """Lazy load Resend client."""
        if self._resend is None:
            try:
                import resend
                resend.api_key = self.api_key
                self._resend = resend
            except ImportError:
                raise ImportError("resend package not installed. Run: uv add resend")
        return self._resend
    
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    def get_tool_definition(self) -> dict:
        """Return MCP-compatible tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }
    
    def execute(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> dict:
        """
        Execute the send_email tool.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC list
            bcc: Optional BCC list
            reply_to: Optional reply-to address
        
        Returns:
            dict with status, id, and message
        """
        if not self.is_configured():
            return {
                "status": "error",
                "message": "Resend API key not configured. Set RESEND_API_KEY in .env"
            }
        
        try:
            # Build email params
            params = {
                "from": self.sender,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "text": body,
            }
            
            if html_body:
                params["html"] = html_body
            
            if cc:
                params["cc"] = cc
            
            if bcc:
                params["bcc"] = bcc
            
            if reply_to or self.reply_to:
                params["reply_to"] = reply_to or self.reply_to
            
            # Send via Resend
            response = self.resend.Emails.send(params)
            
            return {
                "status": "success",
                "id": response.get("id"),
                "message": f"Email sent successfully to {to}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def send_incident_report(
        self,
        to: str,
        alert_id: str,
        service_name: str,
        root_cause: str,
        rca_report: str,
        severity: float = 0.5,
        status: str = "RESOLVED"
    ) -> dict:
        """
        Send a formatted incident report email.
        
        This is a convenience wrapper for incident notifications.
        """
        severity_label = 'CRITICAL' if severity > 0.7 else 'HIGH' if severity > 0.4 else 'MEDIUM'
        status_emoji = '✅' if status == 'RESOLVED' else '⚠️'
        
        subject = f"[{status}] Incident Report: {service_name} - {alert_id}"
        
        body = f"""
INCIDENT REPORT
===============

Alert ID: {alert_id}
Service: {service_name}
Status: {status_emoji} {status}
Severity: {severity_label} ({severity:.2f})

ROOT CAUSE
----------
{root_cause}

FULL REPORT
-----------
{rca_report}

---
Generated by Autonomous Incident Commander
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: #00D4FF; padding: 25px; border-radius: 12px; }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
        .badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
        .resolved {{ background: #28a745; color: white; }}
        .critical {{ background: #dc3545; color: white; }}
        .section {{ margin: 20px 0; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .severity-{severity_label.lower()} {{ color: {'#dc3545' if severity > 0.7 else '#ffc107' if severity > 0.4 else '#28a745'}; font-weight: bold; }}
        pre {{ background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; white-space: pre-wrap; }}
        .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Incident Report</h1>
        <p><strong>Alert ID:</strong> {alert_id}</p>
        <p><strong>Service:</strong> {service_name}</p>
    </div>
    
    <div class="section">
        <p><span class="badge {'resolved' if status == 'RESOLVED' else 'critical'}">{status_emoji} {status}</span></p>
        <p><strong>Severity:</strong> <span class="severity-{severity_label.lower()}">{severity_label} ({severity:.2f})</span></p>
    </div>
    
    <div class="section">
        <h2 style="color: #1a1a2e;">🔍 Root Cause</h2>
        <p>{root_cause}</p>
    </div>
    
    <div class="section">
        <h2 style="color: #1a1a2e;">📋 Full Report</h2>
        <pre>{rca_report}</pre>
    </div>
    
    <div class="footer">
        <p>Generated by <strong>Autonomous Incident Commander</strong></p>
        <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        
        return self.execute(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body
        )


# ============================================
# LangChain Tool Adapter
# ============================================

def create_langchain_tool():
    """
    Create a LangChain-compatible tool from the MCP email tool.
    This allows direct use in LangGraph agents.
    """
    try:
        from langchain_core.tools import tool
        
        mcp_email = MCPEmailTool()
        
        @tool
        def send_email(
            to: str,
            subject: str,
            body: str,
            html_body: str = None,
        ) -> str:
            """
            Send an email using Resend API (MCP-compatible).
            
            Args:
                to: Recipient email address
                subject: Email subject line
                body: Plain text body
                html_body: Optional HTML body
            
            Returns:
                JSON string with send status
            """
            result = mcp_email.execute(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body
            )
            return json.dumps(result)
        
        return send_email
    
    except ImportError:
        return None


# ============================================
# Convenience Functions
# ============================================

_mcp_email_tool: Optional[MCPEmailTool] = None


def get_mcp_email_tool() -> MCPEmailTool:
    """Get or create the MCP email tool singleton."""
    global _mcp_email_tool
    if _mcp_email_tool is None:
        _mcp_email_tool = MCPEmailTool()
    return _mcp_email_tool


def send_email_mcp(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> dict:
    """Send email using MCP tool (convenience function)."""
    return get_mcp_email_tool().execute(
        to=to,
        subject=subject,
        body=body,
        html_body=html_body
    )


def send_incident_email_mcp(
    to: str,
    alert_id: str,
    service_name: str,
    root_cause: str,
    rca_report: str,
    severity: float = 0.5,
    status: str = "RESOLVED"
) -> dict:
    """Send incident report email using MCP tool."""
    return get_mcp_email_tool().send_incident_report(
        to=to,
        alert_id=alert_id,
        service_name=service_name,
        root_cause=root_cause,
        rca_report=rca_report,
        severity=severity,
        status=status
    )

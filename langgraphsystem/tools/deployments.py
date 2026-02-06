"""
Mock deployment/CI-CD tools for tracking configuration changes.
In production, this would integrate with deployment systems.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta


def get_recent_deployments(service_name: str, hours: int = 1) -> List[Dict[str, Any]]:
    """
    Get recent deployments and configuration changes.
    This is crucial for correlating incidents with changes.
    """
    
    # Mock deployment data for the demo scenario
    now = datetime.now()
    
    deployments = [
        {
            "id": "deploy-001",
            "service": service_name,
            "timestamp": (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "type": "config_change",
            "has_config_change": True,
            "change_type": "connection_pool",
            "description": "Reduced connection_pool_size from 200 to 100",
            "author": "ci-pipeline",
            "commit": "abc123",
        },
        {
            "id": "deploy-002", 
            "service": service_name,
            "timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "type": "code_deploy",
            "has_config_change": False,
            "change_type": None,
            "description": "Regular code deployment v2.3.1",
            "author": "release-bot",
            "commit": "def456",
        },
    ]
    
    return deployments


def get_deployment_diff(deployment_id: str) -> Dict[str, Any]:
    """Get the configuration diff for a specific deployment."""
    return {
        "deployment_id": deployment_id,
        "changes": [
            {
                "file": "config/database.yml",
                "before": "connection_pool_size: 200",
                "after": "connection_pool_size: 100",
            }
        ]
    }


def recommend_rollback(deployments: List[Dict]) -> Dict[str, Any]:
    """
    Analyze deployments and recommend rollback target.
    """
    config_changes = [d for d in deployments if d.get("has_config_change")]
    
    if config_changes:
        return {
            "recommend_rollback": True,
            "target_deployment": config_changes[0]["id"],
            "reason": f"Recent configuration change: {config_changes[0]['description']}",
            "estimated_impact": "High - direct correlation with incident timeline"
        }
    
    return {
        "recommend_rollback": False,
        "reason": "No recent configuration changes detected"
    }

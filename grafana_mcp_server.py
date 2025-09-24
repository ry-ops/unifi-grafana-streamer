# grafana_mcp_server.py
# MCP Server for Grafana integration
# Handles dashboards, annotations, alerts, and data sources

import os
import json
import requests
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# Load environment
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")  # Service account token
GRAFANA_ORG_ID = int(os.getenv("GRAFANA_ORG_ID", "1"))

mcp = FastMCP("grafana")

def grafana_headers():
    return {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json",
        "X-Grafana-Org-Id": str(GRAFANA_ORG_ID)
    }

def grafana_get(endpoint: str, params: Dict = None) -> Dict[str, Any]:
    """GET request to Grafana API"""
    resp = requests.get(f"{GRAFANA_URL}/api{endpoint}", headers=grafana_headers(), params=params)
    resp.raise_for_status()
    return resp.json()

def grafana_post(endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """POST request to Grafana API"""
    resp = requests.post(f"{GRAFANA_URL}/api{endpoint}", headers=grafana_headers(), json=data)
    resp.raise_for_status()
    return resp.json()

def grafana_put(endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """PUT request to Grafana API"""
    resp = requests.put(f"{GRAFANA_URL}/api{endpoint}", headers=grafana_headers(), json=data)
    resp.raise_for_status()
    return resp.json()

def grafana_delete(endpoint: str) -> Dict[str, Any]:
    """DELETE request to Grafana API"""
    resp = requests.delete(f"{GRAFANA_URL}/api{endpoint}", headers=grafana_headers())
    resp.raise_for_status()
    return resp.json() if resp.text else {"status": "deleted"}

# ========= Health Check =========
@mcp.resource("grafana://health")
async def grafana_health() -> Dict[str, Any]:
    try:
        health = grafana_get("/health")
        org = grafana_get(f"/orgs/{GRAFANA_ORG_ID}")
        return {
            "ok": True,
            "grafana_url": GRAFANA_URL,
            "version": health.get("version"),
            "database": health.get("database"),
            "org_name": org.get("name")
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ========= Dashboards =========
@mcp.resource("grafana://dashboards")
async def list_dashboards() -> List[Dict[str, Any]]:
    """List all dashboards"""
    search_results = grafana_get("/search", {"type": "dash-db"})
    return search_results

@mcp.resource("grafana://dashboard/{uid}")
async def get_dashboard(uid: str) -> Dict[str, Any]:
    """Get dashboard by UID"""
    return grafana_get(f"/dashboards/uid/{uid}")

@mcp.tool()
def create_unifi_dashboard() -> Dict[str, Any]:
    """Create a UniFi monitoring dashboard"""
    dashboard = {
        "dashboard": {
            "title": "UniFi Network Monitor",
            "tags": ["unifi", "network", "monitoring"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Client Connections",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "sum(unifi_event{event_type=\"client_connect\"})",
                            "legendFormat": "Active Connections"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Access Events",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(unifi_event{source=\"access\"}[5m])",
                            "legendFormat": "{{event_type}}"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Camera Events",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(unifi_event{source=\"protect\"}[5m])",
                            "legendFormat": "{{event_type}}"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        },
        "overwrite": True
    }
    
    return grafana_post("/dashboards/db", dashboard)

@mcp.tool()
def update_dashboard(uid: str, title: str = None, panels: List[Dict] = None) -> Dict[str, Any]:
    """Update an existing dashboard"""
    current = grafana_get(f"/dashboards/uid/{uid}")
    dashboard = current["dashboard"]
    
    if title:
        dashboard["title"] = title
    if panels:
        dashboard["panels"] = panels
    
    payload = {"dashboard": dashboard, "overwrite": True}
    return grafana_post("/dashboards/db", payload)

# ========= Annotations =========
@mcp.resource("grafana://annotations")
async def list_annotations(limit: int = 100) -> List[Dict[str, Any]]:
    """List recent annotations"""
    return grafana_get("/annotations", {"limit": limit})

@mcp.tool()
def create_annotation(text: str, tags: List[str] = None, time: int = None) -> Dict[str, Any]:
    """Create a new annotation"""
    import time as time_module
    
    annotation = {
        "text": text,
        "tags": tags or [],
        "time": time or int(time_module.time() * 1000)
    }
    
    return grafana_post("/annotations", annotation)

@mcp.tool()
def create_bulk_annotations(annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create multiple annotations at once"""
    results = []
    for annotation in annotations:
        try:
            result = grafana_post("/annotations", annotation)
            results.append({"success": True, "id": result.get("id")})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total": len(annotations),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }

# ========= Data Sources =========
@mcp.resource("grafana://datasources")
async def list_datasources() -> List[Dict[str, Any]]:
    """List all data sources"""
    return grafana_get("/datasources")

@mcp.tool()
def create_prometheus_datasource(name: str, url: str, default: bool = False) -> Dict[str, Any]:
    """Create a Prometheus data source"""
    datasource = {
        "name": name,
        "type": "prometheus",
        "url": url,
        "access": "proxy",
        "isDefault": default,
        "jsonData": {
            "httpMethod": "POST"
        }
    }
    
    return grafana_post("/datasources", datasource)

# ========= Alerts =========
@mcp.resource("grafana://alerts")
async def list_alert_rules() -> List[Dict[str, Any]]:
    """List all alert rules"""
    return grafana_get("/ruler/grafana/api/v1/rules")

@mcp.tool()
def create_unifi_alert_rule(
    rule_name: str,
    condition: str,
    threshold: float,
    for_duration: str = "5m"
) -> Dict[str, Any]:
    """Create alert rule for UniFi events"""
    
    rule = {
        "uid": f"unifi_{rule_name.lower().replace(' ', '_')}",
        "title": rule_name,
        "condition": "B",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {
                    "from": 600,
                    "to": 0
                },
                "model": {
                    "expr": condition,
                    "interval": "",
                    "refId": "A"
                }
            },
            {
                "refId": "B",
                "queryType": "",
                "relativeTimeRange": {
                    "from": 0,
                    "to": 0
                },
                "model": {
                    "conditions": [
                        {
                            "evaluator": {
                                "params": [threshold],
                                "type": "gt"
                            },
                            "operator": {
                                "type": "and"
                            },
                            "query": {
                                "params": ["A"]
                            },
                            "reducer": {
                                "params": [],
                                "type": "last"
                            },
                            "type": "query"
                        }
                    ],
                    "refId": "B"
                }
            }
        ],
        "noDataState": "NoData",
        "execErrState": "Alerting",
        "for": for_duration,
        "annotations": {
            "description": f"UniFi alert: {rule_name}",
            "summary": f"Alert triggered for {rule_name}"
        },
        "labels": {
            "team": "infrastructure",
            "source": "unifi"
        }
    }
    
    return grafana_post("/ruler/grafana/api/v1/rules/unifi", {
        "name": "unifi",
        "rules": [rule]
    })

# ========= Search & Query =========
@mcp.tool()
def search_grafana(query: str, tags: List[str] = None) -> List[Dict[str, Any]]:
    """Search dashboards, folders, and alerts"""
    params = {"q": query}
    if tags:
        params["tag"] = tags
    
    return grafana_get("/search", params)

@mcp.resource("grafana://folders")
async def list_folders() -> List[Dict[str, Any]]:
    """List all folders"""
    return grafana_get("/folders")

# ========= Real-time Event Handler =========
@mcp.tool()
def handle_unifi_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Handle incoming UniFi events and create appropriate Grafana artifacts"""
    
    # Create annotations for all events
    annotations = []
    alert_worthy_events = []
    
    for event in events:
        # Create annotation
        annotation = {
            "text": event.get("message", "UniFi Event"),
            "tags": [
                event.get("source", "unifi"),
                event.get("event_type", "event"),
                event.get("severity", "info")
            ],
            "time": event.get("timestamp")
        }
        annotations.append(annotation)
        
        # Check if this should trigger an alert
        if event.get("severity") in ["warning", "critical"]:
            alert_worthy_events.append(event)
    
    # Bulk create annotations
    annotation_result = create_bulk_annotations(annotations)
    
    # Handle alerts (could trigger notifications, update dashboards, etc.)
    alert_results = []
    for alert_event in alert_worthy_events:
        # You could create specific alert rules or send notifications here
        alert_results.append({
            "event_id": alert_event.get("id"),
            "action": "logged_for_alerting",
            "severity": alert_event.get("severity")
        })
    
    return {
        "processed_events": len(events),
        "annotations_created": annotation_result,
        "alerts_processed": len(alert_results),
        "alert_details": alert_results
    }

# ========= Setup Helper =========
@mcp.tool()
def setup_unifi_monitoring() -> Dict[str, Any]:
    """One-click setup for UniFi monitoring in Grafana"""
    results = {}
    
    try:
        # 1. Create Prometheus datasource (if not exists)
        existing_ds = grafana_get("/datasources")
        prometheus_exists = any(ds.get("type") == "prometheus" for ds in existing_ds)
        
        if not prometheus_exists:
            prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
            ds_result = create_prometheus_datasource("Prometheus", prometheus_url, True)
            results["datasource"] = ds_result
        else:
            results["datasource"] = "Already exists"
        
        # 2. Create UniFi dashboard
        dashboard_result = create_unifi_dashboard()
        results["dashboard"] = dashboard_result
        
        # 3. Create basic alert rules
        alert_rules = [
            ("UniFi Access Denied", "rate(unifi_event{event_type=\"access_denied\"}[5m])", 0.1),
            ("UniFi Camera Offline", "rate(unifi_event{event_type=\"camera_offline\"}[5m])", 0.05),
            ("UniFi High Client Connections", "sum(unifi_event{event_type=\"client_connect\"})", 50)
        ]
        
        alert_results = []
        for name, condition, threshold in alert_rules:
            try:
                alert_result = create_unifi_alert_rule(name, condition, threshold)
                alert_results.append({"name": name, "status": "created"})
            except Exception as e:
                alert_results.append({"name": name, "status": "failed", "error": str(e)})
        
        results["alerts"] = alert_results
        
        return {"success": True, "setup_results": results}
        
    except Exception as e:
        return {"success": False, "error": str(e), "partial_results": results}

# ========= Prompts =========
@mcp.prompt("setup_unifi_grafana")
def setup_unifi_grafana():
    return {
        "description": "Complete setup guide for UniFi monitoring in Grafana",
        "messages": [{
            "role": "system",
            "content": (
                "To set up UniFi monitoring: 1) Call 'setup_unifi_monitoring' for automatic setup, "
                "2) Configure your UniFi streamer with Grafana credentials, "
                "3) Start the event streamer, 4) Check 'grafana://health' to verify connection."
            )
        }]
    }

if __name__ == "__main__":

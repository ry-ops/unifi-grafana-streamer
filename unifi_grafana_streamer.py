# unifi_grafana_streamer.py
# Real-time UniFi event streaming to Grafana via MCP
# Polls UniFi events and pushes alerts/metrics to Grafana

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import httpx
import os
from pathlib import Path

# Load secrets.env (reuse from main.py)
def load_env_file(env_file: str = "secrets.env"):
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key, value = key.strip(), value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    if key not in os.environ:
                        os.environ[key] = value

load_env_file()

# Configuration
UNIFI_API_KEY = os.getenv("UNIFI_API_KEY")
UNIFI_HOST = os.getenv("UNIFI_GATEWAY_HOST")
UNIFI_PORT = os.getenv("UNIFI_GATEWAY_PORT", "443")
VERIFY_TLS = os.getenv("UNIFI_VERIFY_TLS", "false").lower() in ("1", "true", "yes")

# Grafana configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")  # Service account token

# MCP Grafana server (if using MCP instead of direct API)
GRAFANA_MCP_ENDPOINT = os.getenv("GRAFANA_MCP_ENDPOINT", "http://localhost:8080")

# Polling intervals
EVENT_POLL_INTERVAL = int(os.getenv("EVENT_POLL_INTERVAL", "30"))  # seconds
METRICS_PUSH_INTERVAL = int(os.getenv("METRICS_PUSH_INTERVAL", "60"))  # seconds

# UniFi API endpoints
NET_BASE = f"https://{UNIFI_HOST}:{UNIFI_PORT}/proxy/network/integrations/v1"
ACCESS_BASE = f"https://{UNIFI_HOST}:{UNIFI_PORT}/proxy/access/api/v1"
PROTECT_BASE = f"https://{UNIFI_HOST}:{UNIFI_PORT}/proxy/protect/api"

@dataclass
class UniFiEvent:
    timestamp: str
    event_type: str
    source: str  # 'network', 'access', 'protect'
    site_id: str
    device_id: Optional[str] = None
    client_mac: Optional[str] = None
    severity: str = "info"  # info, warning, critical
    message: str = ""
    metadata: Dict[str, Any] = None

    def to_grafana_annotation(self) -> Dict[str, Any]:
        """Convert to Grafana annotation format"""
        return {
            "time": int(datetime.fromisoformat(self.timestamp.replace('Z', '+00:00')).timestamp() * 1000),
            "text": f"[{self.source.upper()}] {self.message}",
            "tags": [self.event_type, self.source, self.severity],
            "title": f"{self.event_type.title()} Event"
        }

    def to_prometheus_metric(self) -> str:
        """Convert to Prometheus exposition format"""
        labels = [
            f'source="{self.source}"',
            f'event_type="{self.event_type}"',
            f'site_id="{self.site_id}"',
            f'severity="{self.severity}"'
        ]
        if self.device_id:
            labels.append(f'device_id="{self.device_id}"')
        
        timestamp_ms = int(datetime.fromisoformat(self.timestamp.replace('Z', '+00:00')).timestamp() * 1000)
        
        return f'unifi_event{{{"".join(labels)}}} 1 {timestamp_ms}'

class UniFiEventStreamer:
    def __init__(self):
        self.http_client = httpx.AsyncClient(verify=VERIFY_TLS, timeout=30.0)
        self.seen_events: Set[str] = set()
        self.last_poll_time = datetime.now(timezone.utc)
        
        self.headers = {
            "X-API-Key": UNIFI_API_KEY,
            "Content-Type": "application/json"
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    async def get_network_events(self) -> List[UniFiEvent]:
        """Poll Network/Integration API for client events"""
        events = []
        try:
            # Get recent client connections/disconnections
            sites_resp = await self.http_client.get(
                f"{NET_BASE}/sites", headers=self.headers
            )
            sites_resp.raise_for_status()
            sites = sites_resp.json().get("data", [])
            
            for site in sites:
                site_id = site.get("name", "default")
                
                # Get active clients to detect new connections
                clients_resp = await self.http_client.get(
                    f"{NET_BASE}/sites/{site_id}/clients/active", 
                    headers=self.headers
                )
                clients_resp.raise_for_status()
                clients = clients_resp.json().get("data", [])
                
                for client in clients:
                    # Check if this is a new connection (simplified logic)
                    event_id = f"network_connect_{client.get('mac')}_{client.get('last_seen')}"
                    if event_id not in self.seen_events:
                        self.seen_events.add(event_id)
                        
                        events.append(UniFiEvent(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            event_type="client_connect",
                            source="network",
                            site_id=site_id,
                            client_mac=client.get("mac"),
                            severity="info",
                            message=f"Client {client.get('hostname', 'Unknown')} ({client.get('mac')}) connected",
                            metadata={"ip": client.get("ip"), "ap": client.get("ap_mac")}
                        ))
                        
        except Exception as e:
            print(f"Error polling network events: {e}")
            
        return events

    async def get_access_events(self) -> List[UniFiEvent]:
        """Poll Access API for door/reader events"""
        events = []
        try:
            resp = await self.http_client.get(
                f"{ACCESS_BASE}/events",
                headers=self.headers,
                params={"limit": 50, "sort": "-timestamp"}
            )
            resp.raise_for_status()
            access_events = resp.json().get("data", [])
            
            for event in access_events:
                event_id = f"access_{event.get('id')}"
                if event_id not in self.seen_events:
                    self.seen_events.add(event_id)
                    
                    severity = "warning" if event.get("access_granted") is False else "info"
                    
                    events.append(UniFiEvent(
                        timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        event_type=event.get("type", "access_event"),
                        source="access",
                        site_id=event.get("site_id", "default"),
                        device_id=event.get("door_id"),
                        severity=severity,
                        message=f"Access {event.get('type')} at {event.get('door_name', 'Unknown Door')}",
                        metadata={"user": event.get("user_name"), "granted": event.get("access_granted")}
                    ))
                    
        except Exception as e:
            print(f"Error polling access events: {e}")
            
        return events

    async def get_protect_events(self) -> List[UniFiEvent]:
        """Poll Protect API for camera/motion events"""
        events = []
        try:
            # Get recent events (last 24h)
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_time = end_time - (24 * 60 * 60 * 1000)  # 24h ago
            
            resp = await self.http_client.get(
                f"{PROTECT_BASE}/events",
                headers=self.headers,
                params={"start": start_time, "end": end_time, "limit": 100}
            )
            resp.raise_for_status()
            protect_events = resp.json()
            
            if isinstance(protect_events, dict) and "events" in protect_events:
                protect_events = protect_events["events"]
            
            for event in protect_events:
                event_id = f"protect_{event.get('id')}"
                if event_id not in self.seen_events:
                    self.seen_events.add(event_id)
                    
                    severity = "warning" if event.get("type") == "motion" else "info"
                    
                    events.append(UniFiEvent(
                        timestamp=datetime.fromtimestamp(event.get("start", 0) / 1000, tz=timezone.utc).isoformat(),
                        event_type=event.get("type", "camera_event"),
                        source="protect",
                        site_id="default",
                        device_id=event.get("camera"),
                        severity=severity,
                        message=f"Camera event: {event.get('type')} on {event.get('camera_name', 'Unknown Camera')}",
                        metadata={"score": event.get("score"), "duration": event.get("end", 0) - event.get("start", 0)}
                    ))
                    
        except Exception as e:
            print(f"Error polling protect events: {e}")
            
        return events

    async def send_to_grafana_annotations(self, events: List[UniFiEvent]):
        """Send events as Grafana annotations"""
        if not GRAFANA_API_KEY:
            print("No Grafana API key configured, skipping annotations")
            return
            
        try:
            grafana_headers = {
                "Authorization": f"Bearer {GRAFANA_API_KEY}",
                "Content-Type": "application/json"
            }
            
            for event in events:
                annotation = event.to_grafana_annotation()
                
                resp = await self.http_client.post(
                    f"{GRAFANA_URL}/api/annotations",
                    headers=grafana_headers,
                    json=annotation
                )
                resp.raise_for_status()
                print(f"✓ Sent annotation: {event.message}")
                
        except Exception as e:
            print(f"Error sending Grafana annotations: {e}")

    async def send_to_grafana_mcp(self, events: List[UniFiEvent]):
        """Send events to Grafana MCP server"""
        try:
            # This would call your Grafana MCP server
            mcp_payload = {
                "action": "create_annotations",
                "annotations": [event.to_grafana_annotation() for event in events]
            }
            
            resp = await self.http_client.post(
                f"{GRAFANA_MCP_ENDPOINT}/annotations",
                json=mcp_payload
            )
            resp.raise_for_status()
            print(f"✓ Sent {len(events)} events to Grafana MCP")
            
        except Exception as e:
            print(f"Error sending to Grafana MCP: {e}")

    async def push_metrics_to_prometheus(self, events: List[UniFiEvent]):
        """Push metrics to Prometheus pushgateway"""
        prometheus_gateway = os.getenv("PROMETHEUS_PUSHGATEWAY", "http://localhost:9091")
        
        try:
            # Create metrics payload
            metrics = []
            for event in events:
                metrics.append(event.to_prometheus_metric())
            
            if metrics:
                payload = "\n".join(metrics)
                
                resp = await self.http_client.post(
                    f"{prometheus_gateway}/metrics/job/unifi_events",
                    content=payload,
                    headers={"Content-Type": "text/plain"}
                )
                resp.raise_for_status()
                print(f"✓ Pushed {len(metrics)} metrics to Prometheus")
                
        except Exception as e:
            print(f"Error pushing to Prometheus: {e}")

    async def poll_and_stream(self):
        """Main polling loop"""
        print("🚀 Starting UniFi -> Grafana event streamer...")
        print(f"→ Polling interval: {EVENT_POLL_INTERVAL}s")
        print(f"→ UniFi Controller: https://{UNIFI_HOST}:{UNIFI_PORT}")
        print(f"→ Grafana URL: {GRAFANA_URL}")
        
        while True:
            try:
                print(f"\n📡 Polling events at {datetime.now()}")
                
                # Collect events from all sources
                all_events = []
                all_events.extend(await self.get_network_events())
                all_events.extend(await self.get_access_events())
                all_events.extend(await self.get_protect_events())
                
                if all_events:
                    print(f"📨 Found {len(all_events)} new events")
                    
                    # Send to Grafana (choose your method)
                    await self.send_to_grafana_annotations(all_events)
                    # OR: await self.send_to_grafana_mcp(all_events)
                    
                    # Optional: Also push metrics
                    # await self.push_metrics_to_prometheus(all_events)
                else:
                    print("No new events")
                
                # Cleanup old seen events (prevent memory growth)
                if len(self.seen_events) > 10000:
                    # Keep only recent 5000 events
                    self.seen_events = set(list(self.seen_events)[-5000:])
                
                await asyncio.sleep(EVENT_POLL_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n👋 Shutting down streamer...")
                break
            except Exception as e:
                print(f"❌ Error in polling loop: {e}")
                await asyncio.sleep(EVENT_POLL_INTERVAL)

async def main():
    async with UniFiEventStreamer() as streamer:
        await streamer.poll_and_stream()

if __name__ == "__main__":
    asyncio.run(main())

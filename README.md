<img src="https://github.com/ry-ops/UniFi-Grafana-Streamer/blob/main/unifi-grafana-streamer.png?raw=true" width="100%">

# UniFi Grafana MCP Streamer Server

A comprehensive Model Context Protocol (MCP) server for UniFi network infrastructure management with real-time Grafana integration. Monitor and control your UniFi Network, Access, and Protect systems through a unified API interface.

![UniFi MCP Architecture](https://img.shields.io/badge/UniFi-Integration-blue?style=flat-square) ![MCP](https://img.shields.io/badge/MCP-Compatible-green?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square) ![Grafana](https://img.shields.io/badge/Grafana-Ready-orange?style=flat-square)

## Features

### 🌐 UniFi Integration
- **Network Management**: Sites, devices, clients, WLANs via Integration API
- **Access Control**: Doors, readers, users, events management
- **Protect Security**: Cameras, events, streams, NVR monitoring
- **Dual Authentication**: API key + legacy cookie fallback
- **Real-time Health Monitoring**: Multiple health check endpoints

### 📊 Real-time Monitoring
- **Event Streaming**: Live UniFi events to Grafana annotations
- **Metrics Export**: Prometheus-compatible metrics
- **Alert Integration**: Grafana alerting for critical events
- **Dashboard Automation**: Auto-generated UniFi monitoring dashboards

### 🔧 MCP Protocol Support
- **Rich Resources**: Browse UniFi data through standard MCP resources
- **Safe Actions**: Curated tools for network operations
- **Prompt Playbooks**: Ready-to-use automation workflows
- **Multi-source Integration**: Network + Access + Protect unified

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/ry-ops/unifi-mcp-server.git
cd unifi-mcp-server

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Set up project
uv venv
uv add "mcp[cli]" httpx requests
```

### 2. Configuration

Create a `secrets.env` file with your UniFi credentials:

```bash
# UniFi Controller Configuration
UNIFI_API_KEY=your_api_key_here
UNIFI_GATEWAY_HOST=192.168.1.1
UNIFI_GATEWAY_PORT=443
UNIFI_VERIFY_TLS=false

# Optional: Legacy API credentials
UNIFI_USERNAME=admin
UNIFI_PASSWORD=your_password

# Optional: Grafana Integration
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your_grafana_service_account_token
```

### 3. Basic Usage

```bash
# Test the MCP server
uv run python main.py

# Start real-time streaming to Grafana
uv run python unifi_grafana_streamer.py

# Run Grafana MCP server
uv run python grafana_mcp_server.py
```

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UniFi MCP     │    │  Event Streamer │    │ Grafana MCP     │
│     Server      │◄──►│                 │◄──►│     Server      │
│                 │    │  Real-time Poll │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ UniFi Network   │    │   Prometheus    │    │    Grafana      │
│ Access/Protect  │    │   Pushgateway   │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## API Endpoints & Resources

### Network Resources
- `sites://` - List all sites
- `sites://{site_id}/devices` - Network devices
- `sites://{site_id}/clients` - Connected clients  
- `sites://{site_id}/clients/active` - Active clients only
- `sites://{site_id}/wlans` - Wireless networks
- `sites://{site_id}/search/clients/{query}` - Search clients
- `sites://{site_id}/search/devices/{query}` - Search devices

### Access Control Resources  
- `access://doors` - All access doors
- `access://readers` - Card readers
- `access://users` - Access users
- `access://events` - Access events log

### Protect Security Resources
- `protect://nvr` - NVR system info
- `protect://cameras` - All cameras
- `protect://camera/{camera_id}` - Specific camera
- `protect://events` - Security events
- `protect://events/range/{start_ts}/{end_ts}` - Time-ranged events
- `protect://streams/{camera_id}` - Camera stream info

### Health & Debug
- `unifi://health` - Controller health check
- `health://unifi` - Alternative health endpoint  
- `status://unifi` - Status alias
- `unifi://capabilities` - API capability probe

## Available Tools

### Network Management
- `block_client(site_id, mac)` - Block a client device
- `unblock_client(site_id, mac)` - Unblock a client device  
- `kick_client(site_id, mac)` - Disconnect a client
- `locate_device(site_id, device_id, seconds)` - Flash device LEDs
- `wlan_set_enabled_legacy(site_id, wlan_id, enabled)` - Toggle WLAN

### Access Control
- `access_unlock_door(door_id, seconds)` - Momentary door unlock

### Protect Security
- `protect_camera_reboot(camera_id)` - Reboot camera
- `protect_camera_led(camera_id, enabled)` - Toggle status LED
- `protect_toggle_privacy(camera_id, enabled)` - Privacy mode

### System Tools
- `unifi_health()` - Health check tool
- `debug_registry()` - List registered MCP resources

## Real-time Monitoring Setup

### 1. Configure Grafana Integration

```bash
# Add to your secrets.env
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=glsa_your_service_account_token_here
PROMETHEUS_PUSHGATEWAY=http://localhost:9091
```

### 2. Start Event Streaming

```bash
# Start the real-time event streamer
uv run python unifi_grafana_streamer.py
```

### 3. Auto-setup Grafana Dashboard

Using the Grafana MCP server:

```python
# This creates datasources, dashboards, and alert rules
setup_unifi_monitoring()
```

### 4. Monitor Events

The streamer will:
- Poll UniFi APIs every 30 seconds for new events
- Send events as Grafana annotations
- Push metrics to Prometheus
- Create alerts for critical events

## Event Types Monitored

### Network Events
- Client connections/disconnections
- Device status changes  
- WLAN toggles
- Authentication failures

### Access Events
- Door access attempts
- Card reader events
- User access grants/denials
- System status changes

### Protect Events  
- Motion detection
- Smart detections (person, vehicle, etc.)
- Camera status changes
- Recording events

## Prompt Playbooks

The server includes ready-to-use automation workflows:

- `how_to_find_device` - Locate and flash device LEDs
- `how_to_block_client` - Safely block problematic clients
- `how_to_toggle_wlan` - Enable/disable wireless networks
- `how_to_manage_access` - Door access control
- `how_to_find_camera` - Camera discovery and stream info
- `how_to_review_motion` - Motion event analysis
- `how_to_reboot_camera` - Safe camera reboots

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UNIFI_API_KEY` | Yes | - | UniFi Integration API key |
| `UNIFI_GATEWAY_HOST` | Yes | - | Controller IP/hostname |
| `UNIFI_GATEWAY_PORT` | No | 443 | Controller port |
| `UNIFI_VERIFY_TLS` | No | false | Verify SSL certificates |
| `UNIFI_USERNAME` | No | - | Legacy API username |
| `UNIFI_PASSWORD` | No | - | Legacy API password |
| `UNIFI_TIMEOUT_S` | No | 15 | Request timeout seconds |
| `GRAFANA_URL` | No | http://localhost:3000 | Grafana instance URL |
| `GRAFANA_API_KEY` | No | - | Grafana service account token |
| `PROMETHEUS_PUSHGATEWAY` | No | http://localhost:9091 | Prometheus pushgateway |
| `EVENT_POLL_INTERVAL` | No | 30 | Event polling interval (seconds) |

## Getting UniFi API Key

1. **Network/Protect API Key**:
   - Log into your UniFi Controller
   - Go to Settings → Admins  
   - Create new admin user or edit existing
   - Generate API key in user settings

2. **Legacy API** (optional):
   - Used for features not in Integration API
   - Requires admin username/password
   - Falls back automatically when needed

## Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv && \
    uv venv && \
    uv add "mcp[cli]" httpx requests

COPY secrets.env .

CMD ["uv", "run", "python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  unifi-mcp:
    build: .
    environment:
      - UNIFI_API_KEY=${UNIFI_API_KEY}
      - UNIFI_GATEWAY_HOST=${UNIFI_GATEWAY_HOST}
    ports:
      - "8080:8080"
    
  unifi-streamer:
    build: .
    command: ["uv", "run", "python", "unifi_grafana_streamer.py"]
    environment:
      - UNIFI_API_KEY=${UNIFI_API_KEY}
      - GRAFANA_API_KEY=${GRAFANA_API_KEY}
    depends_on:
      - grafana
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Troubleshooting

### Common Issues

1. **API Key Authentication Fails**
   ```bash
   # Verify API key has proper permissions
   curl -H "X-API-Key: YOUR_KEY" https://your-controller:443/proxy/network/integrations/v1/sites
   ```

2. **TLS Certificate Errors**
   ```bash
   # For self-signed certificates
   export UNIFI_VERIFY_TLS=false
   ```

3. **Legacy API Needed**
   ```bash
   # Some features require legacy credentials
   export UNIFI_USERNAME=admin
   export UNIFI_PASSWORD=your_password
   ```

4. **Health Check Fails**
   ```bash
   # Test controller connectivity
   uv run python -c "
   from main import _health_check
   print(_health_check())
   "
   ```

### Debug Mode

```bash
# Enable verbose logging
export UNIFI_DEBUG=true
uv run python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/unifi-mcp-server.git
cd unifi-mcp-server

# Install development dependencies
uv add --dev pytest black isort mypy

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://github.com/anthropics/mcp) by Anthropic
- [FastMCP](https://github.com/jlowin/fastmcp) framework
- UniFi API community documentation
- Grafana Labs for visualization platform

## Support

- 📖 [Documentation](https://github.com/yourusername/unifi-mcp-server/wiki)
- 🐛 [Issue Tracker](https://github.com/yourusername/unifi-mcp-server/issues)  
- 💬 [Discussions](https://github.com/yourusername/unifi-mcp-server/discussions)
- 📧 Email: support@yourproject.com

---

**Made with ❤️ for the UniFi community**

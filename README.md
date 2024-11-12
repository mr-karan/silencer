# silencer

A bot that integrates Mattermost with Alertmanager, allowing users to create silences directly from Mattermost.

## Features

- Create Alertmanager silences via Mattermost slash command
- Flexible duration format (minutes, hours, days, weeks)
- Secure token-based authentication
- Detailed logging

## Installation

Using Docker:
```yaml
services:
  silencer:
    container_name: silencer
    image: mrkaran/silencer:latest
    ports:
      - 7788:7788
    environment:
      - MATTERMOST_TOKEN=your_token_here
      - ALERTMANAGER_URL=https://username:password@alertmanager-url
      - HOST=0.0.0.0  # Optional
      - PORT=7788     # Optional
    restart: always
```


## Configuration

Environment variables:
- `MATTERMOST_TOKEN`: Mattermost slash command token
- `ALERTMANAGER_URL`: Alertmanager API endpoint with basic auth if required
- `HOST`: Host to bind (default: 0.0.0.0)
- `PORT`: Port to listen on (default: 7788)

## Usage

1. Set up slash command in Mattermost:
   - Command: `/silence`
   - Request URL: `http://your-server:7788/silence`
   - Request Method: POST

2. Create silences using:


```
/silence <matcher> <duration> <comment>
```

Examples:
- `/silence alertname=HighCPU,severity=critical 2h CPU alert silenced`
- `/silence instance=server-01 1d Maintenance window`
- `/silence alertname=HighCPU,severity=critical 2h Investigating high CPU usage - TICK-123`

Duration format:
- m: minutes
- h: hours
- d: days
- w: weeks


## Response Format

```
🔕 Alert silenced successfully!
Silence ID: {silence_id}
Matcher: alertname=HighCPU,severity=critical
Duration: 2h
Comment: Investigating high CPU usage - TICK-123
```

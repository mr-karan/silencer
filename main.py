#!/usr/bin/env python3.12
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import httpx
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from typing import Optional
import re
from pydantic import BaseModel
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import timezone

# Configuration using environment variables
@dataclass
class Config:
    MATTERMOST_TOKENS: list[str] = field(default_factory=lambda: [
        token.strip()
        for token in os.environ.get('MATTERMOST_TOKENS', '').split(',')
        if token.strip()
    ])
    ALERTMANAGER_URL: str = os.environ.get('ALERTMANAGER_URL', 'http://alertmanager:9093')
    HOST: str = os.environ.get('HOST', '0.0.0.0')
    PORT: int = int(os.environ.get('PORT', '7788'))

    def get_approved_users(self) -> Optional[list[str]]:
        """Returns list of approved users if ALLOWED_USERS is set, None otherwise"""
        users = os.environ.get('ALLOWED_USERS')
        if not users:
            return None
        return [u.strip() for u in users.split(',') if u.strip()]

class SilenceRequest(BaseModel):
    matcher: str
    duration: str
    comment: str

class MattermostCommand(BaseModel):
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str

def parse_duration(duration_str: str) -> timedelta:
    """Parse duration strings like '2h', '30m', '1d' into timedelta"""
    units = {
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }

    match = re.match(r'^(\d+)([mhdw])$', duration_str)
    if not match:
        raise ValueError("Invalid duration format. Use <number><unit> where unit is m,h,d,w")

    value, unit = match.groups()
    return timedelta(**{units[unit]: int(value)})

async def create_silence(matcher: str, duration: timedelta, comment: str, username: str) -> str:
    """Create a silence in Alertmanager"""
    start_time = datetime.now(timezone.utc)
    end_time = start_time + duration

    silence_data = {
        "matchers": [{"name": label.split("=")[0], "value": label.split("=")[1], "isRegex": False}
                    for label in matcher.split(",")],
        "startsAt": start_time.isoformat(),
        "endsAt": end_time.isoformat(),
        "createdBy": f"mattermost-bot:{username}",
        "comment": f"{comment} (created-by: {username})",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.ALERTMANAGER_URL}/api/v2/silences",
            json=silence_data
        )
        response.raise_for_status()
        return response.json()["silenceID"]

app = FastAPI()
logger = logging.getLogger(__name__)
config = Config()

@app.post("/silence")
async def handle_silence_command(request: Request):
    form_data = await request.form()
    command = MattermostCommand(**form_data)

    # Verify token
    if not config.MATTERMOST_TOKENS:
        logger.error("No Mattermost tokens configured")
        raise HTTPException(status_code=500, detail="No Mattermost tokens configured")
    if command.token not in config.MATTERMOST_TOKENS:
        logger.warning(f"Invalid token received from user: {command.user_name}")
        raise HTTPException(status_code=401, detail="Invalid token")

    # Verify user if ALLOWED_USERS is set
    approved_users = config.get_approved_users()
    if approved_users is not None and command.user_name not in approved_users:
        return {
            "response_type": "ephemeral",
            "text": "You are not authorized to create silences."
        }

    try:
        # Parse command arguments
        args = command.text.split()
        if len(args) < 3:
            return {
                "response_type": "ephemeral",
                "text": "Usage: /silence <matcher> <duration> <comment>\n"
                       "Example: /silence alertname=HighCPU,severity=critical 2h CPU alert silenced"
            }

        matcher = args[0]
        duration_str = args[1]
        comment = " ".join(args[2:])

        # Validate and parse duration
        duration = parse_duration(duration_str)

        # Create silence
        silence_id = await create_silence(matcher, duration, comment, command.user_name)

        response_text = (f"🔕 Alert silenced successfully!\n"
                        f"Silence ID: {silence_id}\n"
                        f"Matcher: {matcher}\n"
                        f"Duration: {duration_str}\n"
                        f"Comment: {comment}\n"
                        f"Created by: {command.user_name}")
        logger.info(f"Successfully created silence: {silence_id} for matcher: {matcher}")
        return {
            "response_type": "in_channel",
            "text": response_text
        }

    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"Validation error in silence command: {error_msg}")
        return {
            "response_type": "ephemeral",
            "text": error_msg
        }
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.exception("Error processing silence command")
        return {
            "response_type": "ephemeral",
            "text": error_msg
        }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Start the server
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info"
    )

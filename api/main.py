"""
Game Analytics API - FastAPI application for receiving game events.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi.responses import JSONResponse

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.security import HTTPBearer

try:
    from models import (
        InstallEventModel, PurchaseEventModel, 
        EventResponse, ErrorResponse, HealthResponse
    )
    from firehose_client import FirehoseClient
except ImportError:
    # Fallback to relative imports
    from .models import (
        InstallEventModel, PurchaseEventModel, 
        EventResponse, ErrorResponse, HealthResponse
    )
    from .firehose_client import FirehoseClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv("API_KEY", "your-api-key-here")
FIREHOSE_STREAM_NAME = os.getenv("FIREHOSE_STREAM_NAME", "game-events-stream") 
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
USE_MOCK_FIREHOSE = os.getenv("USE_MOCK_FIREHOSE", "true").lower() == "true"

# Initialize Firehose client
firehose_client = FirehoseClient(
    stream_name=FIREHOSE_STREAM_NAME,
    region_name=AWS_REGION,
    use_mock=USE_MOCK_FIREHOSE
)

# FastAPI app
app = FastAPI(
    title="Game Analytics API",
    description="API for collecting game events",
    version="1.0.0"
)

# Security
security = HTTPBearer()


def verify_api_key(credentials = Depends(security)):
    """Verify API key."""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials


async def send_to_firehose(event_data: Dict[str, Any]):
    """Send event to Firehose in background."""
    logger.info(f"Background task started for event: {event_data.get('event_id')}")
    try:
        success = firehose_client.send_event(event_data)
        if not success:
            logger.error(f"Failed to send event to Firehose: {event_data.get('event_id')}")
    except Exception as e:
        logger.error(f"Error sending to Firehose: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Game Analytics API", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    firehose_healthy = firehose_client.health_check()
    
    return HealthResponse(
        status="healthy" if firehose_healthy else "degraded",
        timestamp=datetime.utcnow()
    )


@app.post("/events/install", response_model=EventResponse)
async def receive_install_event(
    event: InstallEventModel,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Receive install event."""
    try:
        # Convert to dict and send to Firehose
        event_data = event.model_dump()
        event_data['timestamp'] = event_data['timestamp'].isoformat()
        background_tasks.add_task(send_to_firehose, event_data)
        
        logger.info(f"Install event received: {event.event_id}")
        
        return EventResponse(
            success=True,
            event_id=event.event_id,
            message="Install event received",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing install event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/events/purchase", response_model=EventResponse) 
async def receive_purchase_event(
    event: PurchaseEventModel,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Receive purchase event."""
    try:
        # Convert to dict and send to Firehose
        event_data = event.model_dump()
        event_data['timestamp'] = event_data['timestamp'].isoformat()
        background_tasks.add_task(send_to_firehose, event_data)
        
        logger.info(f"Purchase event received: {event.event_id}")
        
        return EventResponse(
            success=True,
            event_id=event.event_id,
            message="Purchase event received",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing purchase event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "HTTPException", 
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
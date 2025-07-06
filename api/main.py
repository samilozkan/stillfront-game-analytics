"""
Game Analytics API - FastAPI application for receiving game events.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Union
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status, Request
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))


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
# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="Game Analytics API",
    description="API for collecting game events",
    version="1.0.0"
)

# Rate limiter'ı app'e bağla
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer()


def verify_api_key(credentials = Depends(security)):
    """Verify API key."""
    print(f"DEBUG - Expected API_KEY: '{API_KEY}'")
    print(f"DEBUG - Received credentials: '{credentials.credentials}'")
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

async def send_batch_to_firehose(events_data: List[Dict[str, Any]]):
    """Send batch of events to Firehose in background."""
    logger.info(f"Background batch processing started for {len(events_data)} events")
    try:
        success = firehose_client.send_events_batch(events_data)
        if success:
            logger.info(f"Batch processing successful: {len(events_data)} events")
        else:
            logger.error(f"Batch processing failed: {len(events_data)} events")
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Game Analytics API", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Simplified health check for debugging."""
    try:
        # Basit version - sadece temel check
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="error",
            timestamp=datetime.utcnow(),
            version="1.0.0"
        )


@app.post("/events/install", response_model=EventResponse)
@limiter.limit("100/minute")
async def receive_install_event(
    request: Request,
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
@limiter.limit("100/minute")
async def receive_purchase_event(
    request: Request,
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


@app.post("/events/batch")
@limiter.limit("10/minute")
async def receive_events_batch(
    request: Request,
    events: List[Union[InstallEventModel, PurchaseEventModel]],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Receive multiple events in batch."""
    # Validation
    if len(events) > 500:
        raise HTTPException(400, "Batch size cannot exceed 500 events")
    if len(events) == 0:
        raise HTTPException(400, "Batch cannot be empty")
    
    logger.info(f"Batch received with {len(events)} events")
    
    try:
        # Convert all events to dict format
        events_data = []
        for event in events:
            event_data = event.model_dump()
            event_data['timestamp'] = event_data['timestamp'].isoformat()
            events_data.append(event_data)
        
        # Background batch processing
        background_tasks.add_task(send_batch_to_firehose, events_data)
        
        return {
            "success": True,
            "accepted_events": len(events),
            "message": f"Batch of {len(events)} events accepted",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise HTTPException(500, str(e))
    
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
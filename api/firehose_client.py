"""
AWS Kinesis Firehose client for streaming events.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
import backoff

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not available, using mock client")


class FirehoseClient:
    """AWS Kinesis Firehose client."""
    
    def __init__(self, stream_name: str, region_name: str = "us-east-1", 
                 use_mock: bool = False):
        """
        Initialize Firehose client.
        
        Args:
            stream_name: Kinesis Firehose stream name
            region_name: AWS region
            use_mock: Use mock client for testing
        """
        self.stream_name = stream_name
        self.region_name = region_name
        
        if use_mock or not BOTO3_AVAILABLE:
            self.client = MockFirehoseClient()
            logger.info("Using mock Firehose client")
        else:
            try:
                self.client = boto3.client('firehose', region_name=region_name)
                logger.info("Using real AWS Firehose client")
            except Exception as e:
                logger.error(f"Failed to create AWS client: {e}")
                self.client = MockFirehoseClient()
                logger.info("Falling back to mock client")
    
    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Send single event to Firehose."""
        logger.info(f"send_event called with: {event_data.get('event_id')}")
        try:
            # Add metadata
            record_data = {
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'source': 'game_analytics_api',
                **event_data
            }
            
            # Convert to JSON with newline (required for Firehose)
            json_data = json.dumps(record_data) + '\n'
            
            logger.info(f"About to call AWS put_record for stream: {self.stream_name}")
            if hasattr(self.client, 'put_record'):
                # Real AWS client
                response = self.client.put_record(
                    DeliveryStreamName=self.stream_name,
                    Record={'Data': json_data}
                )
                logger.info(f"AWS put_record response: {response}")
                return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
            else:
                # Mock client
                return self.client.send_event(record_data)
                
        except Exception as e:
            logger.error(f"Failed to send event to Firehose: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if Firehose is accessible."""
        try:
            if hasattr(self.client, 'describe_delivery_stream'):
                # Real AWS client
                response = self.client.describe_delivery_stream(
                    DeliveryStreamName=self.stream_name
                )
                status = response.get('DeliveryStreamDescription', {}).get('DeliveryStreamStatus')
                return status == 'ACTIVE'
            else:
                # Mock client
                return self.client.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class MockFirehoseClient:
    """Mock Firehose client for testing."""
    
    def __init__(self):
        self.sent_events = []
        logger.info("Mock Firehose client initialized")
    
    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Mock send event."""
        self.sent_events.append(event_data)
        logger.info(f"Real AWS: Attempting to send event - {event_data.get('event_id')}")
        logger.info(f"Mock: Event sent - {event_data.get('event_id')}")
        return True
    
    def health_check(self) -> bool:
        """Mock health check."""
        return True
    
    def get_sent_events(self):
        """Get all sent events (for testing)."""
        return self.sent_events.copy()
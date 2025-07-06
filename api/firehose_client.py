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

class DeadLetterQueue:
    """Failed events için temporary queue."""
    def __init__(self, max_size: int = 1000):
        self.failed_events = []
        self.max_size = max_size
    
    def add_failed_event(self, event: Dict[str, Any], error: str):
        """Add failed event to queue."""
        if len(self.failed_events) >= self.max_size:
            # En eski eventi sil
            self.failed_events.pop(0)
        
        failed_event = {
            "event": event,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        self.failed_events.append(failed_event)
        logger.warning(f"Event added to DLQ: {event.get('event_id')}")


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
                self.dlq = DeadLetterQueue() # Temporary queue for failed events
                
    
    # Decorator to retry on exceptions with exponential backoff
    @backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=3
    )
    
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
            self.dlq.add_failed_event(event_data, str(e))
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

    def send_events_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Send multiple events in batch."""
        if not events:
            return True
    
        logger.info(f"Sending batch of {len(events)} events")

        # AWS Firehose max 500 records per batch
        batch_size = 500
        all_success = True
    
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            success = self._send_single_batch(batch)
            if not success:
                all_success = False
    
        return all_success

    def _send_single_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Send a single batch of events."""
        records = []
        for event in events:
            record_data = {
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'source': 'game_analytics_api',
                **event
            }
            records.append({'Data': json.dumps(record_data) + '\n'})
    
        try:
            if hasattr(self.client, 'put_record_batch'):
                # Real AWS client
                response = self.client.put_record_batch(
                    DeliveryStreamName=self.stream_name,
                    Records=records
                )
                failed_count = response.get('FailedPutCount', 0)
                if failed_count > 0:
                    logger.warning(f"Batch had {failed_count} failed records")
                return failed_count == 0
            else:
                # Mock client - simulate batch success
                for event in events:
                    self.client.send_event(event)
                return True
            
        except Exception as e:
            logger.error(f"Batch send failed: {e}")
            # Add all events to DLQ
            for event in events:
                self.dlq.add_failed_event(event, str(e))
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
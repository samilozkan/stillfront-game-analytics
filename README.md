# Game Event Tracking System

A Python-based system for tracking mobile game events with SDK and REST API that streams data to AWS Kinesis Firehose for eventual storage in Snowflake.

## 🏗️ Architecture Overview

```
Game Clients → Python SDK → REST API → Kinesis Firehose → S3 → Snowflake
```

This system implements an event-driven architecture for real-time game analytics, designed to handle high-volume event streams with proper validation, authentication, and scalability.

## 📦 Project Structure

```
game_event_tracking/
├── sdk/
│   ├── __init__.py         # SDK package exports
│   ├── events.py           # Event data models (InstallEvent, PurchaseEvent)
│   └── client.py           # HTTP client for sending events
├── api/
│   ├── main.py             # FastAPI application with endpoints
│   ├── models.py           # Pydantic models for validation
│   └── firehose_client.py  # AWS Kinesis Firehose client
├── tests/
│   ├── test_sdk.py         # SDK unit tests (9 tests)
│   └── test_api.py         # API integration tests (8 tests)
└── README.md               # This documentation
```

## 🚀 How to Use the SDK

### 1. Installation

```bash
# Install dependencies
pip install fastapi uvicorn pydantic requests boto3

# Set environment variables
export API_KEY="your-api-key"
export FIREHOSE_STREAM_NAME="game-events-stream"
export AWS_REGION="eu-north-1"
export USE_MOCK_FIREHOSE="false"  # Use real AWS services
```

### 2. SDK Usage

```python
from sdk import GameAnalyticsClient, InstallEvent, PurchaseEvent

# Initialize client
client = GameAnalyticsClient(
    base_url="https://your-api-endpoint.com",
    api_key="your-api-key"
)

# Send install event
install_event = InstallEvent(
    user_id="user_12345",
    game_id="awesome_game",
    platform="ios", 
    app_version="1.2.0",
    session_id="session_abc123",
    source="organic",
    country="US"
)
success = client.send_install_event(install_event)

# Send purchase event (multi-currency support)
purchase_event = PurchaseEvent(
    user_id="user_12345",
    game_id="awesome_game",
    platform="ios",
    app_version="1.2.0", 
    session_id="session_abc123",
    product_id="coin_pack_1000",
    product_name="1000 Gold Coins",
    price=4.99,
    currency="USD",  # Supports multiple currencies
    store="app_store"
)
success = client.send_purchase_event(purchase_event)
```

### 3. Start the API

```bash
cd api
python main.py
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## 🎯 Design Decisions

### Event Schema Design
- **Inheritance-based Events**: `BaseEvent` class with `InstallEvent` and `PurchaseEvent` subclasses for extensibility
- **Strong Typing**: Dataclasses with validation for reliability
- **UUID Generation**: Automatic event ID generation to prevent duplicates
- **ISO Timestamps**: UTC timestamps in ISO format for consistency
- **Multi-currency Support**: Native support for different currencies with optional USD conversion

### API Architecture
- **FastAPI Framework**: Modern async Python framework for high performance
- **Pydantic Validation**: Automatic request/response validation and serialization
- **Background Tasks**: Non-blocking Firehose delivery using FastAPI background tasks
- **Bearer Token Auth**: Simple but effective authentication mechanism
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

### Data Pipeline
- **AWS Kinesis Firehose**: Real-time streaming with automatic batching and compression
- **S3 Storage**: Intermediate storage with partitioned structure for efficient querying
- **JSON Format**: Human-readable format with metadata injection for debugging
- **Mock Client**: Development-friendly mock for testing without AWS costs

### Code Structure
- **Modular Design**: Separate packages for SDK, API, and tests
- **Dependency Injection**: Configurable clients and services
- **Error Resilience**: Retry logic and graceful degradation
- **Test Coverage**: Comprehensive unit and integration tests

## 📋 Assumptions Made

### Business Assumptions
- **Two Primary Events**: Install and Purchase events cover initial analytics needs
- **Session-based Tracking**: Events are grouped by session for user journey analysis
- **Global Audience**: Multi-currency support needed for international games
- **High Volume**: System designed to handle thousands of events per second

### Technical Assumptions
- **AWS Infrastructure**: Using AWS services for scalability and reliability
- **Python Ecosystem**: Leveraging mature Python libraries for rapid development
- **JSON Format**: Choosing JSON over Avro/Protobuf for simplicity and debugging
- **HTTP Protocol**: REST API over gRPC for broader client compatibility

### Operational Assumptions
- **Bearer Token Auth**: Simple authentication sufficient for MVP (JWT for production)
- **Environment Variables**: Configuration via env vars for 12-factor app compliance
- **Mock Support**: Development environment doesn't require real AWS services
- **Snowflake Integration**: Future data warehouse needs structured for SQL analytics

## 🏢 Snowflake Multi-Currency Design

### Core Tables Schema

```sql
-- Events landing table (from Firehose)
CREATE TABLE raw_events (
    event_id STRING NOT NULL,
    event_type STRING NOT NULL,
    user_id STRING NOT NULL,
    game_id STRING NOT NULL,
    timestamp TIMESTAMP_NTZ NOT NULL,
    platform STRING NOT NULL,
    event_data VARIANT,  -- Flexible JSON storage
    ingestion_timestamp TIMESTAMP_NTZ NOT NULL
) PARTITION BY DATE(timestamp);

-- Purchase events with multi-currency support
CREATE TABLE purchase_events (
    event_id STRING PRIMARY KEY,
    user_id STRING NOT NULL,
    game_id STRING NOT NULL, 
    timestamp TIMESTAMP_NTZ NOT NULL,
    
    -- Product information
    product_id STRING NOT NULL,
    product_name STRING NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    
    -- Multi-currency pricing
    price DECIMAL(10,2) NOT NULL,           -- Original price
    currency STRING NOT NULL,               -- ISO 4217 code (USD, EUR, GBP, JPY)
    exchange_rate DECIMAL(10,6),            -- Exchange rate to USD
    revenue_usd DECIMAL(10,2),              -- Converted revenue for analysis
    
    -- Transaction metadata
    transaction_id STRING,
    store STRING,                           -- app_store, google_play, steam
    platform STRING NOT NULL
) PARTITION BY DATE(timestamp);

-- Currency exchange rates table
CREATE TABLE currency_rates (
    currency_code STRING NOT NULL,         -- ISO 4217
    rate_date DATE NOT NULL,
    usd_rate DECIMAL(10,6) NOT NULL,       -- Rate to convert to USD
    source STRING DEFAULT 'external_api',
    
    PRIMARY KEY (currency_code, rate_date)
);

-- User dimension table
CREATE TABLE users (
    user_id STRING PRIMARY KEY,
    first_install_date DATE,
    install_source STRING,
    install_country STRING,
    total_purchases INTEGER DEFAULT 0,
    lifetime_revenue_usd DECIMAL(10,2) DEFAULT 0,
    last_seen_date DATE
);
```

### Multi-Currency Handling Strategy

```sql
-- Revenue aggregation with currency conversion
CREATE VIEW daily_revenue AS
SELECT 
    DATE(timestamp) as event_date,
    game_id,
    platform,
    currency,
    COUNT(*) as purchase_count,
    SUM(price) as total_revenue_original,
    SUM(revenue_usd) as total_revenue_usd,
    COUNT(DISTINCT user_id) as paying_users
FROM purchase_events 
GROUP BY DATE(timestamp), game_id, platform, currency;

-- Currency conversion procedure
CREATE OR REPLACE PROCEDURE convert_currency_to_usd(start_date DATE, end_date DATE)
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- Update purchase events with USD conversion
    UPDATE purchase_events p
    SET 
        exchange_rate = r.usd_rate,
        revenue_usd = p.price / r.usd_rate
    FROM currency_rates r
    WHERE p.currency = r.currency_code
      AND DATE(p.timestamp) = r.rate_date
      AND DATE(p.timestamp) BETWEEN start_date AND end_date
      AND p.revenue_usd IS NULL;
    
    RETURN 'Currency conversion completed';
END;
$$;
```

### Data Pipeline Integration

```
Kinesis Firehose → S3 (events/) → Snowpipe → raw_events → 
DBT/Stored Procedures → Structured Tables → Analytics Views
```

## 🔧 What's Next for Production-Ready

### Immediate Priorities (Sprint 1)
1. **Authentication Enhancement**
   - JWT tokens with expiration and refresh
   - API key rotation mechanism
   - Rate limiting per client

2. **Error Handling & Monitoring**
   - Structured logging with correlation IDs
   - Prometheus metrics export
   - Dead letter queues for failed events
   - Health check endpoints with dependency status

3. **Data Validation & Schema**
   - JSON Schema validation for events
   - Schema registry for version management
   - Backward compatibility checks

### Performance & Scalability (Sprint 2)
1. **High Throughput Optimization**
   - Batch API endpoints (100+ events per request)
   - Connection pooling and HTTP/2
   - Async SDK client with event batching
   - Kinesis Firehose buffer optimization

2. **Infrastructure**
   - Container deployment (Docker + Kubernetes)
   - Auto-scaling policies
   - Multi-region deployment
   - CDN for SDK distribution

3. **Data Pipeline Enhancements**
   - Real-time alerting on data quality issues
   - Automatic schema drift detection
   - Data lineage tracking

### Advanced Features (Sprint 3+)
1. **Analytics & ML**
   - Real-time event processing (Apache Kafka/Kinesis Analytics)
   - Anomaly detection for fraud prevention
   - User segmentation and cohort analysis
   - Revenue forecasting models

2. **Operational Excellence**
   - Chaos engineering tests
   - Automated rollback mechanisms
   - Blue-green deployments
   - End-to-end testing automation

3. **Compliance & Security**
   - GDPR compliance (data deletion, anonymization)
   - SOC 2 Type II certification readiness
   - Encryption at rest and in transit
   - Audit logging

## 🧪 Testing

```bash
# Run all tests
export PYTHONPATH=.
python -m pytest tests/ -v

# SDK tests (9 tests)
python -m pytest tests/test_sdk.py -v

# API tests (8 tests) 
python -m pytest tests/test_api.py -v

# Test coverage
python -m pytest tests/ --cov=sdk --cov=api
```

## 📊 Current Implementation Status

**✅ Completed:**
- SDK with event models and HTTP client
- FastAPI REST API with validation
- AWS Kinesis Firehose integration (real + mock)
- Comprehensive test suite (17 tests)
- Multi-currency purchase events
- Background task processing
- Authentication middleware
- Error handling

**🔄 Demonstrated (not implemented):**
- Snowflake schema design
- Production deployment architecture
- Advanced monitoring and alerting
- ML/Analytics pipeline integration

## 🎯 Success Metrics

The system successfully demonstrates:
- **Real-time data flow**: Events → API → Firehose → S3 (verified with actual data)
- **Scalable architecture**: Async processing with proper error handling
- **Production patterns**: Authentication, validation, testing, documentation
- **Multi-currency support**: Ready for global game deployment
- **Developer experience**: Simple SDK with clear error messages

This foundation supports millions of events per day with proper monitoring and scaling infrastructure.

---

**Time Investment**: ~5 hours (within 3-5 hour requirement)
- Architecture & SDK: 1.5 hours
- API & AWS Integration: 2 hours  
- Testing & Debugging: 1 hour
- Documentation: 0.5 hours
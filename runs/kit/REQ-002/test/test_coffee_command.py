"""
Tests for /coffee command handler
"""

import hashlib
import hmac
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, Request

from runs.kit.REQ_002.src.handlers.coffee_command import (
    CoffeeCommandHandler,
    SlackSignatureValidator,
)
from runs.kit.REQ_002.src.services.kafka_producer_interface import (
    KafkaProducerInterface,
)


class MockKafkaProducer(KafkaProducerInterface):
    """Mock Kafka producer for testing."""

    def __init__(self):
        self.published_events = []

    async def publish(
        self,
        topic: str,
        key: str,
        value: Dict[str, Any],
        headers: Dict[str, str] | None = None,
    ) -> None:
        """Record published events."""
        self.published_events.append(
            {"topic": topic, "key": key, "value": value, "headers": headers}
        )


@pytest.fixture
def signing_secret():
    """Slack signing secret for tests."""
    return "test_signing_secret_12345"


@pytest.fixture
def signature_validator(signing_secret):
    """Signature validator fixture."""
    return SlackSignatureValidator(signing_secret)


@pytest.fixture
def kafka_producer():
    """Mock Kafka producer fixture."""
    return MockKafkaProducer()


@pytest.fixture
def handler(signature_validator, kafka_producer):
    """CoffeeCommandHandler fixture."""
    return CoffeeCommandHandler(signature_validator, kafka_producer)


def create_slack_signature(
    signing_secret: str, timestamp: str, body: str
) -> str:
    """
    Create valid Slack signature for testing.

    Args:
        signing_secret: Slack signing secret
        timestamp: Request timestamp
        body: Request body

    Returns:
        Slack signature string
    """
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = (
        "v0="
        + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )
    return signature


@pytest.mark.asyncio
async def test_valid_signature_returns_modal(
    handler, signing_secret, kafka_producer
):
    """Test that valid signature returns modal response."""
    # Arrange
    timestamp = str(int(time.time()))
    body = (
        "token=test_token&team_id=T123&channel_id=C123&"
        "user_id=U123&command=/coffee&trigger_id=12345.67890"
    )
    signature = create_slack_signature(signing_secret, timestamp, body)

    # Mock request
    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }
    request.body = AsyncMock(return_value=body.encode())
    request.form = AsyncMock(
        return_value={
            "trigger_id": "12345.67890",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "command": "/coffee",
        }
    )

    # Act
    response = await handler.handle(request)

    # Assert
    assert response["trigger_id"] == "12345.67890"
    assert response["view"]["type"] == "modal"
    assert response["view"]["callback_id"] == "coffee_order_modal"
    assert len(response["view"]["blocks"]) == 3  # drink, size, customizations

    # Verify Kafka event published
    assert len(kafka_producer.published_events) == 1
    event = kafka_producer.published_events[0]
    assert event["topic"] == "slack.events"
    assert event["key"] == "U123"
    assert event["value"]["event_type"] == "slack.command.received"
    assert event["value"]["command"] == "/coffee"


@pytest.mark.asyncio
async def test_invalid_signature_raises_401(handler, signing_secret):
    """Test that invalid signature raises 401."""
    # Arrange
    timestamp = str(int(time.time()))
    body = "token=test_token&user_id=U123"
    invalid_signature = "v0=invalid_signature"

    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": invalid_signature,
    }
    request.body = AsyncMock(return_value=body.encode())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(request)
    assert exc_info.value.status_code == 401
    assert "Invalid signature" in exc_info.value.detail


@pytest.mark.asyncio
async def test_old_timestamp_raises_401(handler, signing_secret):
    """Test that old timestamp raises 401 (replay attack prevention)."""
    # Arrange
    old_timestamp = str(int(time.time()) - 400)  # 400 seconds old
    body = "token=test_token&user_id=U123"
    signature = create_slack_signature(signing_secret, old_timestamp, body)

    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": old_timestamp,
        "X-Slack-Signature": signature,
    }
    request.body = AsyncMock(return_value=body.encode())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(request)
    assert exc_info.value.status_code == 401
    assert "timestamp too old" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_modal_contains_required_fields(handler, signing_secret):
    """Test that modal contains all required fields."""
    # Arrange
    timestamp = str(int(time.time()))
    body = (
        "token=test_token&team_id=T123&channel_id=C123&"
        "user_id=U123&command=/coffee&trigger_id=12345.67890"
    )
    signature = create_slack_signature(signing_secret, timestamp, body)

    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }
    request.body = AsyncMock(return_value=body.encode())
    request.form = AsyncMock(
        return_value={
            "trigger_id": "12345.67890",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "command": "/coffee",
        }
    )

    # Act
    response = await handler.handle(request)

    # Assert modal structure
    blocks = response["view"]["blocks"]

    # Check drink type block
    drink_block = next(
        b for b in blocks if b["block_id"] == "drink_type_block"
    )
    assert drink_block["accessory"]["type"] == "static_select"
    assert len(drink_block["accessory"]["options"]) >= 5  # Multiple drinks

    # Check size block
    size_block = next(b for b in blocks if b["block_id"] == "size_block")
    assert size_block["accessory"]["type"] == "radio_buttons"
    assert len(size_block["accessory"]["options"]) == 3  # Small, Medium, Large

    # Check customizations block
    custom_block = next(
        b for b in blocks if b["block_id"] == "customizations_block"
    )
    assert custom_block["element"]["type"] == "plain_text_input"
    assert custom_block["optional"] is True


@pytest.mark.asyncio
async def test_kafka_failure_does_not_block_response(
    signature_validator, signing_secret
):
    """Test that Kafka publish failure does not block user response."""
    # Arrange
    failing_producer = Mock(spec=KafkaProducerInterface)
    failing_producer.publish = AsyncMock(
        side_effect=Exception("Kafka unavailable")
    )
    handler = CoffeeCommandHandler(signature_validator, failing_producer)

    timestamp = str(int(time.time()))
    body = (
        "token=test_token&team_id=T123&channel_id=C123&"
        "user_id=U123&command=/coffee&trigger_id=12345.67890"
    )
    signature = create_slack_signature(signing_secret, timestamp, body)

    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }
    request.body = AsyncMock(return_value=body.encode())
    request.form = AsyncMock(
        return_value={
            "trigger_id": "12345.67890",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "command": "/coffee",
        }
    )

    # Act - should not raise exception
    response = await handler.handle(request)

    # Assert - modal still returned
    assert response["trigger_id"] == "12345.67890"
    assert response["view"]["type"] == "modal"


@pytest.mark.asyncio
async def test_response_time_under_2_seconds(handler, signing_secret):
    """Test that response time is under 2 seconds (AC requirement)."""
    # Arrange
    timestamp = str(int(time.time()))
    body = (
        "token=test_token&team_id=T123&channel_id=C123&"
        "user_id=U123&command=/coffee&trigger_id=12345.67890"
    )
    signature = create_slack_signature(signing_secret, timestamp, body)

    request = Mock(spec=Request)
    request.headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }
    request.body = AsyncMock(return_value=body.encode())
    request.form = AsyncMock(
        return_value={
            "trigger_id": "12345.67890",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "command": "/coffee",
        }
    )

    # Act
    start_time = time.time()
    response = await handler.handle(request)
    elapsed_time = time.time() - start_time

    # Assert
    assert elapsed_time < 2.0  # Must respond within 2 seconds
    assert response["view"]["type"] == "modal"
```

```python
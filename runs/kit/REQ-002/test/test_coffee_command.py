"""
Unit tests for /coffee slash command handler.

Tests signature validation, modal response, and Kafka event publishing.
"""
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from ..src.handlers.coffee_command import CoffeeCommandHandler, SlackSignatureValidator


class TestSlackSignatureValidator:
    """Test suite for Slack signature validation."""

    @pytest.fixture
    def signing_secret(self) -> str:
        return "test_signing_secret_12345"

    @pytest.fixture
    def validator(self, signing_secret: str) -> SlackSignatureValidator:
        return SlackSignatureValidator(signing_secret)

    def test_valid_signature(self, validator: SlackSignatureValidator, signing_secret: str) -> None:
        """Test that valid signature passes validation."""
        timestamp = str(int(time.time()))
        body = b"token=test&command=/coffee&user_id=U123"

        # Compute valid signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        signature = "v0=" + hmac.new(
            signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()

        assert validator.validate(timestamp, body, signature) is True

    def test_invalid_signature(self, validator: SlackSignatureValidator) -> None:
        """Test that invalid signature fails validation."""
        timestamp = str(int(time.time()))
        body = b"token=test&command=/coffee&user_id=U123"
        signature = "v0=invalid_signature"

        assert validator.validate(timestamp, body, signature) is False

    def test_replay_attack_prevention(self, validator: SlackSignatureValidator) -> None:
        """Test that old timestamps are rejected."""
        old_timestamp = str(int(time.time()) - 400)  # 6+ minutes old
        body = b"token=test&command=/coffee&user_id=U123"
        signature = "v0=dummy"

        with pytest.raises(HTTPException) as exc_info:
            validator.validate(old_timestamp, body, signature)

        assert exc_info.value.status_code == 401
        assert "timestamp too old" in exc_info.value.detail.lower()


class TestCoffeeCommandHandler:
    """Test suite for /coffee command handler."""

    @pytest.fixture
    def mock_validator(self) -> Mock:
        validator = Mock(spec=SlackSignatureValidator)
        validator.validate.return_value = True
        return validator

    @pytest.fixture
    def mock_kafka_producer(self) -> AsyncMock:
        producer = AsyncMock()
        producer.publish = AsyncMock()
        return producer

    @pytest.fixture
    def handler(self, mock_validator: Mock, mock_kafka_producer: AsyncMock) -> CoffeeCommandHandler:
        return CoffeeCommandHandler(mock_validator, mock_kafka_producer)

    @pytest.fixture
    def mock_request(self) -> Mock:
        request = Mock()
        request.headers = {
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "v0=test_signature",
        }
        request.body = AsyncMock(return_value=b"test_body")
        request.form = AsyncMock(
            return_value={
                "trigger_id": "trigger_123",
                "user_id": "U123",
                "channel_id": "C123",
                "team_id": "T123",
                "command": "/coffee",
            }
        )
        return request

    @pytest.mark.asyncio
    async def test_successful_command_handling(
        self, handler: CoffeeCommandHandler, mock_request: Mock, mock_kafka_producer: AsyncMock
    ) -> None:
        """Test successful /coffee command handling."""
        response = await handler.handle(mock_request)

        # Verify signature validation was called
        assert mock_request.body.called

        # Verify Kafka event was published
        mock_kafka_producer.publish.assert_called_once()
        call_args = mock_kafka_producer.publish.call_args
        assert call_args.kwargs["topic"] == "slack.events"
        assert call_args.kwargs["key"] == "U123"
        assert call_args.kwargs["value"]["event_type"] == "slash_command"
        assert call_args.kwargs["value"]["command"] == "/coffee"
        assert "correlation_id" in call_args.kwargs["headers"]

        # Verify modal response structure
        assert response["trigger_id"] == "trigger_123"
        assert response["view"]["type"] == "modal"
        assert response["view"]["callback_id"] == "coffee_order_modal"
        assert len(response["view"]["blocks"]) == 3  # drink_type, size, customizations

    @pytest.mark.asyncio
    async def test_invalid_signature_rejection(
        self, mock_validator: Mock, mock_kafka_producer: AsyncMock, mock_request: Mock
    ) -> None:
        """Test that invalid signature raises 401."""
        mock_validator.validate.return_value = False
        handler = CoffeeCommandHandler(mock_validator, mock_kafka_producer)

        with pytest.raises(HTTPException) as exc_info:
            await handler.handle(mock_request)

        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_kafka_publish_failure_graceful_degradation(
        self, handler: CoffeeCommandHandler, mock_request: Mock, mock_kafka_producer: AsyncMock
    ) -> None:
        """Test that Kafka publish failure doesn't prevent modal response."""
        mock_kafka_producer.publish.side_effect = Exception("Kafka unavailable")

        # Should not raise exception, returns modal anyway
        response = await handler.handle(mock_request)

        assert response["trigger_id"] == "trigger_123"
        assert response["view"]["type"] == "modal"

    def test_modal_response_structure(self, handler: CoffeeCommandHandler) -> None:
        """Test modal response contains all required fields."""
        modal = handler._build_modal_response("trigger_123")

        assert modal["trigger_id"] == "trigger_123"
        view = modal["view"]

        # Verify modal metadata
        assert view["type"] == "modal"
        assert view["callback_id"] == "coffee_order_modal"
        assert view["title"]["text"] == "Coffee Order"
        assert view["submit"]["text"] == "Submit"

        # Verify blocks
        blocks = view["blocks"]
        assert len(blocks) == 3

        # Drink type block
        drink_block = blocks[0]
        assert drink_block["block_id"] == "drink_type_block"
        assert drink_block["element"]["type"] == "static_select"
        assert len(drink_block["element"]["options"]) >= 5

        # Size block
        size_block = blocks[1]
        assert size_block["block_id"] == "size_block"
        assert size_block["element"]["type"] == "radio_buttons"
        assert len(size_block["element"]["options"]) == 3

        # Customizations block
        custom_block = blocks[2]
        assert custom_block["block_id"] == "customizations_block"
        assert custom_block["element"]["type"] == "plain_text_input"
        assert custom_block["optional"] is True
```

```markdown
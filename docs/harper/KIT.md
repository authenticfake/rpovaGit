# KIT Output — REQ-002: Slack Command Handler `/coffee`

```file:/runs/kit/REQ-002/src/handlers/coffee_command.py
"""
Slack Command Handler for /coffee

Handles the /coffee slash command by:
1. Validating Slack request signature
2. Publishing event to Kafka
3. Returning modal view to Slack

Dependencies injected via constructor (DIP).
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class KafkaProducerProtocol(Protocol):
    """Interface for Kafka event publishing."""

    async def publish(self, topic: str, key: str, value: dict, headers: dict | None = None) -> None:
        """Publish event to Kafka topic."""
        ...


class SlackSignatureValidator:
    """Validates Slack request signatures using HMAC-SHA256."""

    def __init__(self, signing_secret: str):
        self.signing_secret = signing_secret.encode()

    def validate(self, timestamp: str, body: str, signature: str) -> bool:
        """
        Validate Slack request signature.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            body: Raw request body
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        # Reject old requests (replay attack prevention)
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning("Request timestamp too old")
            return False

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body}".encode()
        expected_signature = "v0=" + hmac.new(
            self.signing_secret, sig_basestring, hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_signature, signature)


class CoffeeCommandHandler:
    """Handles /coffee slash command requests."""

    def __init__(
        self,
        signature_validator: SlackSignatureValidator,
        kafka_producer: KafkaProducerProtocol,
        kafka_topic: str = "slack.events",
    ):
        self.signature_validator = signature_validator
        self.kafka_producer = kafka_producer
        self.kafka_topic = kafka_topic

    async def handle(
        self,
        timestamp: str,
        signature: str,
        body: str,
        command_payload: dict,
    ) -> dict:
        """
        Process /coffee command.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header
            body: Raw request body for signature validation
            command_payload: Parsed command data

        Returns:
            Slack modal response or error

        Raises:
            ValueError: If signature validation fails
        """
        # Validate signature
        if not self.signature_validator.validate(timestamp, body, signature):
            logger.error("Invalid Slack signature")
            raise ValueError("Invalid request signature")

        # Extract command data
        trigger_id = command_payload.get("trigger_id")
        user_id = command_payload.get("user_id")
        channel_id = command_payload.get("channel_id")
        team_id = command_payload.get("team_id")

        if not trigger_id:
            raise ValueError("Missing trigger_id in command payload")

        # Publish event to Kafka
        correlation_id = f"{team_id}:{user_id}:{int(time.time() * 1000)}"
        event = {
            "event_type": "slash_command",
            "command": "/coffee",
            "user_id": user_id,
            "channel_id": channel_id,
            "team_id": team_id,
            "trigger_id": trigger_id,
            "timestamp": timestamp,
        }

        await self.kafka_producer.publish(
            topic=self.kafka_topic,
            key=user_id,
            value=event,
            headers={"correlation_id": correlation_id},
        )

        logger.info(
            "Published /coffee command event",
            extra={
                "user_id": user_id,
                "channel_id": channel_id,
                "correlation_id": correlation_id,
            },
        )

        # Return modal view
        return self._build_modal_response(trigger_id)

    def _build_modal_response(self, trigger_id: str) -> dict:
        """
        Build Slack modal view for order submission.

        Args:
            trigger_id: Slack trigger_id for opening modal

        Returns:
            Modal view payload
        """
        return {
            "trigger_id": trigger_id,
            "view": {
                "type": "modal",
                "callback_id": "coffee_order_modal",
                "title": {"type": "plain_text", "text": "Coffee Order"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "drink_type_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "drink_type",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select drink type",
                            },
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "Espresso"},
                                    "value": "espresso",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Latte"},
                                    "value": "latte",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Cappuccino"},
                                    "value": "cappuccino",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Americano"},
                                    "value": "americano",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Mocha"},
                                    "value": "mocha",
                                },
                            ],
                        },
                        "label": {"type": "plain_text", "text": "Drink Type"},
                    },
                    {
                        "type": "input",
                        "block_id": "size_block",
                        "element": {
                            "type": "radio_buttons",
                            "action_id": "size",
                            "options": [
                                {
                                    "text": {"type": "plain_text", "text": "Small"},
                                    "value": "small",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Medium"},
                                    "value": "medium",
                                },
                                {
                                    "text": {"type": "plain_text", "text": "Large"},
                                    "value": "large",
                                },
                            ],
                        },
                        "label": {"type": "plain_text", "text": "Size"},
                    },
                    {
                        "type": "input",
                        "block_id": "customizations_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customizations",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g., extra shot, oat milk, no sugar",
                            },
                        },
                        "label": {"type": "plain_text", "text": "Customizations"},
                        "optional": True,
                    },
                ],
            },
        }
```

```file:/runs/kit/REQ-002/src/api/slack_routes.py
"""
FastAPI routes for Slack slash commands.

Integrates CoffeeCommandHandler with FastAPI.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status

from .coffee_command import CoffeeCommandHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


async def get_command_handler(request: Request) -> CoffeeCommandHandler:
    """Dependency injection for CoffeeCommandHandler."""
    return request.app.state.coffee_command_handler


@router.post("/commands")
async def handle_slash_command(
    request: Request,
    x_slack_request_timestamp: Annotated[str, Header()],
    x_slack_signature: Annotated[str, Header()],
    command: Annotated[str, Form()],
    text: Annotated[str, Form()] = "",
    user_id: Annotated[str, Form()] = "",
    channel_id: Annotated[str, Form()] = "",
    team_id: Annotated[str, Form()] = "",
    trigger_id: Annotated[str, Form()] = "",
    handler: CoffeeCommandHandler = Depends(get_command_handler),
):
    """
    Handle Slack slash commands.

    Validates signature and delegates to appropriate handler.
    """
    # Read raw body for signature validation
    body = await request.body()
    body_str = body.decode("utf-8")

    # Build command payload
    command_payload = {
        "command": command,
        "text": text,
        "user_id": user_id,
        "channel_id": channel_id,
        "team_id": team_id,
        "trigger_id": trigger_id,
    }

    # Only handle /coffee command
    if command != "/coffee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown command: {command}",
        )

    try:
        response = await handler.handle(
            timestamp=x_slack_request_timestamp,
            signature=x_slack_signature,
            body=body_str,
            command_payload=command_payload,
        )
        return response
    except ValueError as e:
        logger.error("Command validation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Command handling failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
```

```file:/runs/kit/REQ-002/src/infrastructure/kafka_producer.py
"""
Kafka producer implementation.

Wraps aiokafka for event publishing with retry logic.
"""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Async Kafka producer with retry logic."""

    def __init__(
        self,
        bootstrap_servers: str,
        max_retries: int = 3,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.max_retries = max_retries
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        """Initialize Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started", extra={"servers": self.bootstrap_servers})

    async def stop(self):
        """Shutdown Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(
        self,
        topic: str,
        key: str,
        value: dict,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Publish event to Kafka topic with retry.

        Args:
            topic: Kafka topic name
            key: Message key (for partitioning)
            value: Message payload (will be JSON serialized)
            headers: Optional message headers

        Raises:
            KafkaError: If publish fails after retries
        """
        if not self._producer:
            raise RuntimeError("Producer not started")

        # Convert headers to bytes
        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                await self._producer.send_and_wait(
                    topic=topic,
                    key=key,
                    value=value,
                    headers=kafka_headers,
                )
                logger.debug(
                    "Published event to Kafka",
                    extra={"topic": topic, "key": key, "attempt": attempt + 1},
                )
                return
            except KafkaError as e:
                last_error = e
                logger.warning(
                    "Kafka publish failed, retrying",
                    extra={
                        "topic": topic,
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                )

        # All retries exhausted
        logger.error(
            "Kafka publish failed after retries",
            extra={"topic": topic, "key": key, "retries": self.max_retries},
        )
        raise last_error
```

```file:/runs/kit/REQ-002/test/test_coffee_command.py
"""
Unit tests for CoffeeCommandHandler.

Tests signature validation, modal response, and Kafka event publishing.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, Mock

import pytest

from runs.kit.REQ_002.src.handlers.coffee_command import (
    CoffeeCommandHandler,
    SlackSignatureValidator,
)


@pytest.fixture
def signing_secret():
    return "test_signing_secret_12345"


@pytest.fixture
def signature_validator(signing_secret):
    return SlackSignatureValidator(signing_secret)


@pytest.fixture
def mock_kafka_producer():
    producer = AsyncMock()
    producer.publish = AsyncMock()
    return producer


@pytest.fixture
def handler(signature_validator, mock_kafka_producer):
    return CoffeeCommandHandler(
        signature_validator=signature_validator,
        kafka_producer=mock_kafka_producer,
        kafka_topic="slack.events",
    )


def generate_valid_signature(signing_secret: str, timestamp: str, body: str) -> str:
    """Generate valid Slack signature for testing."""
    sig_basestring = f"v0:{timestamp}:{body}".encode()
    signature = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring, hashlib.sha256
    ).hexdigest()
    return signature


class TestSlackSignatureValidator:
    def test_valid_signature(self, signature_validator, signing_secret):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        assert signature_validator.validate(timestamp, body, signature) is True

    def test_invalid_signature(self, signature_validator):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123"
        signature = "v0=invalid_signature"

        assert signature_validator.validate(timestamp, body, signature) is False

    def test_old_timestamp_rejected(self, signature_validator, signing_secret):
        # Timestamp from 10 minutes ago
        timestamp = str(int(time.time()) - 600)
        body = "token=test&command=/coffee&user_id=U123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        assert signature_validator.validate(timestamp, body, signature) is False

    def test_replay_attack_prevention(self, signature_validator, signing_secret):
        # Valid signature but old timestamp
        timestamp = str(int(time.time()) - 400)
        body = "token=test&command=/coffee&user_id=U123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        assert signature_validator.validate(timestamp, body, signature) is False


class TestCoffeeCommandHandler:
    @pytest.mark.asyncio
    async def test_handle_valid_command(
        self, handler, signing_secret, mock_kafka_producer
    ):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123&trigger_id=T123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        command_payload = {
            "command": "/coffee",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "trigger_id": "trigger_123",
        }

        response = await handler.handle(timestamp, signature, body, command_payload)

        # Verify Kafka publish called
        mock_kafka_producer.publish.assert_called_once()
        call_args = mock_kafka_producer.publish.call_args
        assert call_args.kwargs["topic"] == "slack.events"
        assert call_args.kwargs["key"] == "U123"
        assert call_args.kwargs["value"]["event_type"] == "slash_command"
        assert call_args.kwargs["value"]["command"] == "/coffee"
        assert "correlation_id" in call_args.kwargs["headers"]

        # Verify modal response
        assert response["trigger_id"] == "trigger_123"
        assert response["view"]["type"] == "modal"
        assert response["view"]["callback_id"] == "coffee_order_modal"

    @pytest.mark.asyncio
    async def test_handle_invalid_signature(self, handler):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123"
        signature = "v0=invalid"

        command_payload = {
            "command": "/coffee",
            "user_id": "U123",
            "trigger_id": "T123",
        }

        with pytest.raises(ValueError, match="Invalid request signature"):
            await handler.handle(timestamp, signature, body, command_payload)

    @pytest.mark.asyncio
    async def test_handle_missing_trigger_id(
        self, handler, signing_secret, mock_kafka_producer
    ):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        command_payload = {
            "command": "/coffee",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            # Missing trigger_id
        }

        with pytest.raises(ValueError, match="Missing trigger_id"):
            await handler.handle(timestamp, signature, body, command_payload)

    def test_modal_structure(self, handler):
        modal = handler._build_modal_response("trigger_123")

        # Verify modal structure
        assert modal["trigger_id"] == "trigger_123"
        view = modal["view"]
        assert view["type"] == "modal"
        assert view["callback_id"] == "coffee_order_modal"

        # Verify blocks
        blocks = view["blocks"]
        assert len(blocks) == 3

        # Drink type block
        drink_block = blocks[0]
        assert drink_block["block_id"] == "drink_type_block"
        assert drink_block["element"]["type"] == "static_select"
        assert len(drink_block["element"]["options"]) == 5

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

    @pytest.mark.asyncio
    async def test_kafka_publish_failure_propagates(
        self, handler, signing_secret, mock_kafka_producer
    ):
        timestamp = str(int(time.time()))
        body = "token=test&command=/coffee&user_id=U123"
        signature = generate_valid_signature(signing_secret, timestamp, body)

        command_payload = {
            "command": "/coffee",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "trigger_id": "trigger_123",
        }

        # Simulate Kafka failure
        mock_kafka_producer.publish.side_effect = Exception("Kafka unavailable")

        with pytest.raises(Exception, match="Kafka unavailable"):
            await handler.handle(timestamp, signature, body, command_payload)
```

```file:/runs/kit/REQ-002/test/test_api_routes.py
"""
Integration tests for Slack command API routes.

Tests FastAPI endpoint with mocked dependencies.
"""

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from runs.kit.REQ_002.src.api.slack_routes import router
from runs.kit.REQ_002.src.handlers.coffee_command import (
    CoffeeCommandHandler,
    SlackSignatureValidator,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def signing_secret():
    return "test_secret_12345"


@pytest.fixture
def mock_kafka_producer():
    producer = AsyncMock()
    producer.publish = AsyncMock()
    return producer


@pytest.fixture
def command_handler(signing_secret, mock_kafka_producer):
    validator = SlackSignatureValidator(signing_secret)
    return CoffeeCommandHandler(
        signature_validator=validator,
        kafka_producer=mock_kafka_producer,
    )


@pytest.fixture
def client(app, command_handler):
    app.state.coffee_command_handler = command_handler
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8080")


def generate_signature(secret: str, timestamp: str, body: str) -> str:
    sig_basestring = f"v0:{timestamp}:{body}".encode()
    return "v0=" + hmac.new(secret.encode(), sig_basestring, hashlib.sha256).hexdigest()


class TestSlackCommandsEndpoint:
    @pytest.mark.asyncio
    async def test_coffee_command_success(self, client, signing_secret):
        timestamp = str(int(time.time()))
        form_data = {
            "command": "/coffee",
            "text": "",
            "user_id": "U123",
            "channel_id": "C123",
            "team_id": "T123",
            "trigger_id": "trigger_123",
        }

        # Generate body string for signature
        body_parts = [f"{k}={v}" for k, v in form_data.items()]
        body = "&".join(body_parts)
        signature = generate_signature(signing_secret, timestamp, body)

        response = await client.post(
            "/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trigger_id"] == "trigger_123"
        assert data["view"]["type"] == "modal"

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_401(self, client):
        timestamp = str(int(time.time()))
        form_data = {
            "command": "/coffee",
            "user_id": "U123",
            "trigger_id": "trigger_123",
        }

        response = await client.post(
            "/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": "v0=invalid",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_command_returns_400(self, client, signing_secret):
        timestamp = str(int(time.time()))
        form_data = {
            "command": "/unknown",
            "user_id": "U123",
            "trigger_id": "trigger_123",
        }

        body = "&".join([f"{k}={v}" for k, v in form_data.items()])
        signature = generate_signature(signing_secret, timestamp, body)

        response = await client.post(
            "/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

        assert response.status_code == 400
        assert "Unknown command" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_trigger_id_returns_500(self, client, signing_secret):
        timestamp = str(int(time.time()))
        form_data = {
            "command": "/coffee",
            "user_id": "U123",
            # Missing trigger_id
        }

        body = "&".join([f"{k}={v}" for k, v in form_data.items()])
        signature = generate_signature(signing_secret, timestamp, body)

        response = await client.post(
            "/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

        assert response.status_code == 500
```

```file:/runs/kit/REQ-002/test/test_kafka_producer.py
"""
Unit tests for KafkaEventProducer.

Tests event publishing and retry logic.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiokafka.errors import KafkaError

from runs.kit.REQ_002.src.infrastructure.kafka_producer import KafkaEventProducer


@pytest.fixture
def producer():
    return KafkaEventProducer(
        bootstrap_servers="localhost:9092",
        max_retries=3,
    )


class TestKafkaEventProducer:
    @pytest.mark.asyncio
    async def test_start_initializes_producer(self, producer):
        with patch("runs.kit.REQ_002.src.infrastructure.kafka_producer.AIOKafkaProducer") as mock_class:
            mock_instance = AsyncMock()
            mock_class.return_value = mock_instance

            await producer.start()

            mock_instance.start.assert_called_once()
            assert producer._producer is not None

    @pytest.mark.asyncio
    async def test_stop_shuts_down_producer(self, producer):
        mock_producer = AsyncMock()
        producer._producer = mock_producer

        await producer.stop()

        mock_producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_success(self, producer):
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()
        producer._producer = mock_producer

        await producer.publish(
            topic="test.topic",
            key="key123",
            value={"event": "test"},
            headers={"correlation_id": "corr123"},
        )

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args.kwargs["topic"] == "test.topic"
        assert call_args.kwargs["key"] == "key123"
        assert call_args.kwargs["value"] == {"event": "test"}

    @pytest.mark.asyncio
    async def test_publish_retry_on_failure(self, producer):
        mock_producer = AsyncMock()
        # Fail twice, succeed on third attempt
        mock_producer.send_and_wait = AsyncMock(
            side_effect=[
                KafkaError("Connection failed"),
                KafkaError("Connection failed"),
                None,  # Success
            ]
        )
        producer._producer = mock_producer

        await producer.publish(
            topic="test.topic",
            key="key123",
            value={"event": "test"},
        )

        assert mock_producer.send_and_wait.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_fails_after_max_retries(self, producer):
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(
            side_effect=KafkaError("Connection failed")
        )
        producer._producer = mock_producer

        with pytest.raises(KafkaError):
            await producer.publish(
                topic="test.topic",
                key="key123",
                value={"event": "test"},
            )

        assert mock_producer.send_and_wait.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_without_start_raises_error(self, producer):
        with pytest.raises(RuntimeError, match="Producer not started"):
            await producer.publish(
                topic="test.topic",
                key="key123",
                value={"event": "test"},
            )
```

```file:/runs/kit/REQ-002/ci/LTC.json
{
  "version": "1.0",
  "req_id": "REQ-002",
  "lane": "python",
  "env": {
    "PYTHONPATH": ".",
    "SLACK_SIGNING_SECRET": "test_secret_placeholder",
    "KAFKA_BROKERS": "localhost:9092"
  },
  "cases": [
    {
      "name": "unit_tests",
      "run": "pytest -p no:cacheprovider -q runs/kit/REQ-002/test/test_coffee_command.py runs/kit/REQ-002/test/test_kafka_producer.py --tb=short",
      "cwd": ".",
      "expect": 0,
      "timeout": 60
    },
    {
      "name": "integration_tests",
      "run": "pytest -p no:cacheprovider -q runs/kit/REQ-002/test/test_api_routes.py --tb=short",
      "cwd": ".",
      "expect": 0,
      "timeout": 60
    },
    {
      "name": "lint",
      "run": "ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test",
      "cwd": ".",
      "expect": 0,
      "timeout": 30
    },
    {
      "name": "type_check",
      "run": "mypy runs/kit/REQ-002/src --strict --ignore-missing-imports",
      "cwd": ".",
      "expect": 0,
      "timeout": 30
    }
  ],
  "reports": [
    {
      "kind": "junit",
      "path": "reports/junit-REQ-002.xml",
      "format": "junit-xml"
    },
    {
      "kind": "coverage",
      "path": "reports/coverage-REQ-002.xml
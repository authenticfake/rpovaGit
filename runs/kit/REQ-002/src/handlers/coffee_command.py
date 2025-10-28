"""
Slack Command Handler for /coffee

Handles the /coffee slash command by:
1. Validating Slack request signature
2. Publishing event to Kafka
3. Returning modal view to user

Follows composition-first design with injected dependencies.
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Protocol

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class KafkaProducerProtocol(Protocol):
    """Protocol for Kafka producer dependency."""

    async def publish(self, topic: str, key: str, value: dict, headers: dict | None = None) -> None:
        """Publish event to Kafka topic."""
        ...


class SlackSignatureValidator:
    """Validates Slack request signatures using HMAC-SHA256."""

    def __init__(self, signing_secret: str):
        """
        Initialize validator with Slack signing secret.

        Args:
            signing_secret: Slack app signing secret from environment
        """
        self.signing_secret = signing_secret.encode()

    def validate(self, timestamp: str, body: bytes, signature: str) -> bool:
        """
        Validate Slack request signature.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            body: Raw request body bytes
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid, False otherwise

        Raises:
            HTTPException: If timestamp is too old (replay attack prevention)
        """
        # Prevent replay attacks - reject requests older than 5 minutes
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            raise HTTPException(status_code=401, detail="Request timestamp too old")

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = (
            "v0=" + hmac.new(self.signing_secret, sig_basestring.encode(), hashlib.sha256).hexdigest()
        )

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)


class CoffeeCommandHandler:
    """Handles /coffee slash command with signature validation and event publishing."""

    def __init__(
        self,
        signature_validator: SlackSignatureValidator,
        kafka_producer: KafkaProducerProtocol,
        kafka_topic: str = "slack.events",
    ):
        """
        Initialize handler with injected dependencies.

        Args:
            signature_validator: Slack signature validator
            kafka_producer: Kafka producer for event publishing
            kafka_topic: Kafka topic for Slack events
        """
        self.signature_validator = signature_validator
        self.kafka_producer = kafka_producer
        self.kafka_topic = kafka_topic

    async def handle(self, request: Request) -> dict:
        """
        Handle /coffee slash command request.

        Args:
            request: FastAPI request object

        Returns:
            Slack modal view response

        Raises:
            HTTPException: If signature validation fails
        """
        # Extract headers
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Read raw body for signature validation
        body = await request.body()

        # Validate signature
        if not self.signature_validator.validate(timestamp, body, signature):
            logger.warning("Invalid Slack signature", extra={"timestamp": timestamp})
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse form data
        form_data = await request.form()
        trigger_id = form_data.get("trigger_id")
        user_id = form_data.get("user_id")
        channel_id = form_data.get("channel_id")
        team_id = form_data.get("team_id")
        command = form_data.get("command")

        # Publish event to Kafka for async processing
        event_payload = {
            "event_type": "slash_command",
            "command": command,
            "trigger_id": trigger_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "team_id": team_id,
            "timestamp": timestamp,
        }

        correlation_id = f"{user_id}_{int(time.time() * 1000)}"
        headers = {"correlation_id": correlation_id}

        try:
            await self.kafka_producer.publish(
                topic=self.kafka_topic, key=user_id, value=event_payload, headers=headers
            )
            logger.info(
                "Published slash command event",
                extra={"correlation_id": correlation_id, "user_id": user_id, "command": command},
            )
        except Exception as e:
            logger.error("Failed to publish event to Kafka", extra={"error": str(e)}, exc_info=True)
            # Continue to return modal even if Kafka publish fails (graceful degradation)

        # Return modal view response
        return self._build_modal_response(trigger_id)

    def _build_modal_response(self, trigger_id: str) -> dict:
        """
        Build Slack modal view for order submission.

        Args:
            trigger_id: Slack trigger_id for opening modal

        Returns:
            Slack view.open API payload
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
                            "placeholder": {"type": "plain_text", "text": "Select drink type"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "Espresso"}, "value": "espresso"},
                                {"text": {"type": "plain_text", "text": "Latte"}, "value": "latte"},
                                {"text": {"type": "plain_text", "text": "Cappuccino"}, "value": "cappuccino"},
                                {"text": {"type": "plain_text", "text": "Americano"}, "value": "americano"},
                                {"text": {"type": "plain_text", "text": "Mocha"}, "value": "mocha"},
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
                                {"text": {"type": "plain_text", "text": "Small"}, "value": "small"},
                                {"text": {"type": "plain_text", "text": "Medium"}, "value": "medium"},
                                {"text": {"type": "plain_text", "text": "Large"}, "value": "large"},
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


def create_coffee_command_handler(
    signing_secret: str, kafka_producer: KafkaProducerProtocol
) -> CoffeeCommandHandler:
    """
    Factory function to create CoffeeCommandHandler with dependencies.

    Args:
        signing_secret: Slack app signing secret
        kafka_producer: Kafka producer instance

    Returns:
        Configured CoffeeCommandHandler instance
    """
    validator = SlackSignatureValidator(signing_secret)
    return CoffeeCommandHandler(validator, kafka_producer)
```

```markdown
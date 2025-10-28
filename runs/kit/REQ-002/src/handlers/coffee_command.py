"""
Slack Command Handler for /coffee

Handles the /coffee slash command, validates Slack signature,
publishes event to Kafka, and returns a modal for order submission.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class SlackSignatureValidator:
    """Validates Slack request signatures using HMAC-SHA256."""

    def __init__(self, signing_secret: str):
        """
        Initialize validator with Slack signing secret.

        Args:
            signing_secret: Slack app signing secret from environment
        """
        self.signing_secret = signing_secret.encode()

    def validate(
        self,
        timestamp: str,
        body: bytes,
        signature: str,
    ) -> bool:
        """
        Validate Slack request signature.

        Args:
            timestamp: X-Slack-Request-Timestamp header value
            body: Raw request body bytes
            signature: X-Slack-Signature header value

        Returns:
            True if signature is valid, False otherwise

        Raises:
            HTTPException: If timestamp is too old (replay attack prevention)
        """
        # Prevent replay attacks - reject requests older than 5 minutes
        current_time = int(time.time())
        request_time = int(timestamp)
        if abs(current_time - request_time) > 300:
            raise HTTPException(
                status_code=401,
                detail="Request timestamp too old",
            )

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = (
            "v0="
            + hmac.new(
                self.signing_secret,
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)


class CoffeeCommandHandler:
    """Handles /coffee slash command from Slack."""

    def __init__(
        self,
        signature_validator: SlackSignatureValidator,
        kafka_producer: Any,  # KafkaProducer interface
    ):
        """
        Initialize handler with dependencies.

        Args:
            signature_validator: Slack signature validator
            kafka_producer: Kafka producer for publishing events
        """
        self.signature_validator = signature_validator
        self.kafka_producer = kafka_producer

    async def handle(self, request: Request) -> Dict[str, Any]:
        """
        Handle /coffee slash command.

        Args:
            request: FastAPI request object

        Returns:
            Slack modal response payload

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
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse form data
        form_data = await request.form()
        trigger_id = form_data.get("trigger_id")
        user_id = form_data.get("user_id")
        channel_id = form_data.get("channel_id")
        team_id = form_data.get("team_id")
        command = form_data.get("command")

        # Publish event to Kafka for audit/processing
        event = {
            "event_type": "slack.command.received",
            "command": command,
            "user_id": user_id,
            "channel_id": channel_id,
            "team_id": team_id,
            "trigger_id": trigger_id,
            "timestamp": timestamp,
        }

        try:
            await self.kafka_producer.publish(
                topic="slack.events",
                key=user_id,
                value=event,
            )
        except Exception as e:
            logger.error(f"Failed to publish event to Kafka: {e}")
            # Continue - Kafka failure should not block user interaction

        # Return modal response
        modal = self._build_order_modal(trigger_id)
        return modal

    def _build_order_modal(self, trigger_id: str) -> Dict[str, Any]:
        """
        Build Slack modal for order submission.

        Args:
            trigger_id: Slack trigger_id for opening modal

        Returns:
            Slack modal payload
        """
        return {
            "trigger_id": trigger_id,
            "view": {
                "type": "modal",
                "callback_id": "coffee_order_modal",
                "title": {"type": "plain_text", "text": "Coffee Order"},
                "submit": {"type": "plain_text", "text": "Submit Order"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "section",
                        "block_id": "drink_type_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Select your drink type:",
                        },
                        "accessory": {
                            "type": "static_select",
                            "action_id": "drink_type",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Choose a drink",
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Espresso",
                                    },
                                    "value": "espresso",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Latte",
                                    },
                                    "value": "latte",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Cappuccino",
                                    },
                                    "value": "cappuccino",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Americano",
                                    },
                                    "value": "americano",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Mocha",
                                    },
                                    "value": "mocha",
                                },
                            ],
                        },
                    },
                    {
                        "type": "section",
                        "block_id": "size_block",
                        "text": {"type": "mrkdwn", "text": "Select size:"},
                        "accessory": {
                            "type": "radio_buttons",
                            "action_id": "size",
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Small",
                                    },
                                    "value": "small",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Medium",
                                    },
                                    "value": "medium",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Large",
                                    },
                                    "value": "large",
                                },
                            ],
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "customizations_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Customizations (optional)",
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customizations",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g., extra shot, oat milk, no sugar",
                            },
                        },
                        "optional": True,
                    },
                ],
            },
        }


# FastAPI route integration
async def coffee_command_route(
    request: Request,
    handler: CoffeeCommandHandler,
) -> Dict[str, Any]:
    """
    FastAPI route for /coffee command.

    Args:
        request: FastAPI request
        handler: CoffeeCommandHandler instance (injected)

    Returns:
        Slack modal response
    """
    return await handler.handle(request)
```

```python
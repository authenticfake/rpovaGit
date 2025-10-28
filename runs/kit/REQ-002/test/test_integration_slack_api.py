"""
Integration tests for Slack API interaction.

Tests full request/response cycle with mocked Slack API.
"""
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ..src.api.slack_routes import router


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app with Slack routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def valid_slack_request_data() -> dict:
    """Generate valid Slack slash command request data."""
    return {
        "token": "test_token",
        "team_id": "T123",
        "team_domain": "test",
        "channel_id": "C123",
        "channel_name": "general",
        "user_id": "U123",
        "user_name": "testuser",
        "command": "/coffee",
        "text": "",
        "response_url": "https://hooks.slack.com/commands/123",
        "trigger_id": "trigger_123.456.789",
    }


@pytest.mark.asyncio
async def test_coffee_command_endpoint_success(app: FastAPI, valid_slack_request_data: dict) -> None:
    """Test /coffee command endpoint returns modal within 2 seconds."""
    with patch("runs.kit.REQ_002.src.api.slack_routes._kafka_producer") as mock_producer:
        mock_producer.publish = AsyncMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8080") as client:
            # Prepare request with valid signature
            timestamp = str(int(time.time()))
            body = "&".join(f"{k}={v}" for k, v in valid_slack_request_data.items())

            # Mock signature validation by patching validator
            with patch(
                "runs.kit.REQ_002.src.handlers.coffee_command.SlackSignatureValidator.validate",
                return_value=True,
            ):
                start_time = time.time()
                response = await client.post(
                    "/slack/commands/coffee",
                    data=valid_slack_request_data,
                    headers={
                        "X-Slack-Request-Timestamp": timestamp,
                        "X-Slack-Signature": "v0=test_signature",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                elapsed = time.time() - start_time

            # Verify response time (AC: within 2 seconds)
            assert elapsed < 2.0, f"Response took {elapsed:.2f}s, expected < 2s"

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["trigger_id"] == "trigger_123.456.789"
            assert data["view"]["type"] == "modal"


@pytest.mark.asyncio
async def test_coffee_command_invalid_signature(app: FastAPI, valid_slack_request_data: dict) -> None:
    """Test that invalid signature returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8080") as client:
        timestamp = str(int(time.time()))

        # Use invalid signature
        with patch(
            "runs.kit.REQ_002.src.handlers.coffee_command.SlackSignatureValidator.validate",
            return_value=False,
        ):
            response = await client.post(
                "/slack/commands/coffee",
                data=valid_slack_request_data,
                headers={
                    "X-Slack-Request-Timestamp": timestamp,
                    "X-Slack-Signature": "v0=invalid_signature",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]
```

```markdown
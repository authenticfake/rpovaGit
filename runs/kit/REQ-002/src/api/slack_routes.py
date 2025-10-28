"""
FastAPI routes for Slack slash commands.

Wires up the /coffee command handler with dependency injection.
"""
import logging
import os

from fastapi import APIRouter, Request

from ..handlers.coffee_command import CoffeeCommandHandler, create_coffee_command_handler
from ..services.kafka_producer import create_kafka_producer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# Initialize dependencies from environment
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")

# Create handler instance (singleton pattern for this module)
_kafka_producer = create_kafka_producer(KAFKA_BROKERS)
_coffee_handler = create_coffee_command_handler(SLACK_SIGNING_SECRET, _kafka_producer)


@router.post("/commands/coffee")
async def coffee_command(request: Request) -> dict:
    """
    Handle /coffee slash command.

    Returns:
        Slack modal view response
    """
    return await _coffee_handler.handle(request)
```

```markdown
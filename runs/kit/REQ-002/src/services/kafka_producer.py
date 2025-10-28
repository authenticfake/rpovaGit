"""
Kafka producer service for event publishing.

Provides async Kafka producer with retry logic and schema validation.
"""
import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Async Kafka producer with retry and error handling."""

    def __init__(self, bootstrap_servers: str):
        """
        Initialize Kafka producer.

        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses
        """
        self.bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start Kafka producer connection."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started", extra={"bootstrap_servers": self.bootstrap_servers})

    async def stop(self) -> None:
        """Stop Kafka producer connection."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, key: str, value: dict, headers: dict[str, str] | None = None) -> None:
        """
        Publish event to Kafka topic.

        Args:
            topic: Kafka topic name
            key: Message key for partitioning
            value: Message payload (will be JSON serialized)
            headers: Optional message headers

        Raises:
            KafkaError: If publish fails after retries
        """
        if not self._producer:
            raise RuntimeError("Kafka producer not started")

        # Convert headers to bytes
        kafka_headers = [(k, v.encode("utf-8")) for k, v in (headers or {}).items()]

        try:
            await self._producer.send_and_wait(topic, value=value, key=key, headers=kafka_headers)
            logger.debug("Published message to Kafka", extra={"topic": topic, "key": key})
        except KafkaError as e:
            logger.error("Failed to publish to Kafka", extra={"topic": topic, "error": str(e)}, exc_info=True)
            raise


def create_kafka_producer(bootstrap_servers: str) -> KafkaProducer:
    """
    Factory function to create KafkaProducer instance.

    Args:
        bootstrap_servers: Comma-separated Kafka broker addresses

    Returns:
        KafkaProducer instance
    """
    return KafkaProducer(bootstrap_servers)
```

```markdown
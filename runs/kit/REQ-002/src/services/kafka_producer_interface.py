"""
Kafka Producer Interface

Defines the contract for Kafka event publishing.
Actual implementation will be provided by REQ-011.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class KafkaProducerInterface(ABC):
    """Interface for Kafka event producer."""

    @abstractmethod
    async def publish(
        self,
        topic: str,
        key: str,
        value: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish event to Kafka topic.

        Args:
            topic: Kafka topic name
            key: Message key for partitioning
            value: Event payload (will be JSON-serialized)
            headers: Optional message headers

        Raises:
            KafkaPublishError: If publish fails after retries
        """
        pass
```

```python
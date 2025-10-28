"""
Application Configuration

Loads settings from environment variables.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment."""

    def __init__(self):
        """Initialize settings from environment variables."""
        self.slack_signing_secret: str = os.getenv(
            "SLACK_SIGNING_SECRET", ""
        )
        self.kafka_brokers: str = os.getenv(
            "KAFKA_BROKERS", "localhost:9092"
        )
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/coffeebuddy",
        )
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> None:
        """
        Validate required settings.

        Raises:
            ValueError: If required settings are missing
        """
        if not self.slack_signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET is required")


# Global settings instance
settings = Settings()
```

```python
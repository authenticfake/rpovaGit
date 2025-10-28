# REQ-002: Slack Command Handler — `/coffee`

## Overview
Implements the `/coffee` slash command handler for Slack. Validates request signatures, publishes events to Kafka, and returns an interactive modal for order submission.

## Components

### `coffee_command.py`
- **SlackSignatureValidator**: HMAC-SHA256 signature validation with replay attack prevention
- **CoffeeCommandHandler**: Main handler for `/coffee` command
- **coffee_command_route**: FastAPI route integration

### `kafka_producer_interface.py`
- Defines the contract for Kafka event publishing
- Actual implementation provided by REQ-011

### `settings.py`
- Environment-based configuration
- Required: `SLACK_SIGNING_SECRET`, `KAFKA_BROKERS`, `DATABASE_URL`

## Design Decisions

### Composition-First
- **Dependency Injection**: Handler receives `SlackSignatureValidator` and `KafkaProducerInterface` as constructor parameters
- **Interface Segregation**: Kafka producer defined as abstract interface for testability
- **No Inheritance**: All behavior through composition

### Security
- **Signature Validation**: HMAC-SHA256 with constant-time comparison
- **Replay Attack Prevention**: Rejects requests older than 5 minutes
- **No Secrets in Code**: All credentials from environment variables

### Resilience
- **Kafka Failure Tolerance**: Kafka publish failures logged but do not block user response
- **Fast Response**: Modal returned within 2 seconds (AC requirement)

## Testing Strategy

### Unit Tests
- Valid signature returns modal
- Invalid signature raises 401
- Old timestamp raises 401 (replay prevention)
- Modal contains required fields (drink type, size, customizations)
- Kafka failure does not block response
- Response time under 2 seconds

### Test Coverage
- Signature validation logic
- Modal structure and fields
- Error handling paths
- Performance requirements

## Dependencies
- **REQ-001**: Database schema (not directly used, but foundation)
- **REQ-011**: Kafka producer implementation (interface defined here)

## Integration Points
- **Slack API**: Receives slash command webhooks
- **Kafka**: Publishes `slack.events` topic
- **FastAPI**: Route handler integration

## Future Extensions
- User preference pre-fill (REQ-010)
- Rate limiting per user
- Command usage analytics
```

```json
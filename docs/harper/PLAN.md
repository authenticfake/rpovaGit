# PLAN — CoffeeBuddy (On-Prem)

## Plan Snapshot
- **Counts:** 18 total / 18 open / 0 done / 0 deferred
- **Progress:** 0% complete (0 / 18)
- **Checklist:**
  - [x] SPEC aligned
  - [x] Prior REQ reconciled (none exist)
  - [x] Dependencies mapped
  - [x] KIT-readiness per REQ confirmed

## Tracks & Scope Boundaries

**Tracks:**
- **App Track:** Core business logic, Slack integration, API endpoints, event processing, runner assignment algorithm, user preferences, audit logging
- **Infra Track:** Kubernetes deployment, Kong Gateway configuration, Ory Hydra/Kratos setup, Vault integration, Prometheus/Grafana observability (deferred unless blocking App track)

**Out of scope / Deferred:**
- Payment processing and financial transactions
- External vendor API integrations
- Mobile native applications
- Real-time GPS tracking
- Multi-tenant SaaS deployment
- Advanced ML-based order prediction
- Calendar system integration
- Full Infra track implementation (Kong routes, Ory setup, Vault policies) — deferred to post-MVP unless blocking

## REQ-IDs Table

| ID | Title | Acceptance (bullets) | DependsOn [IDs] | Track | Status |
|----|-------|---------------------|-----------------|-------|--------|
| REQ-001 | Database Schema & Migrations | Schema matches SPEC entities<br>Migrations are idempotent<br>Indexes on foreign keys and query paths<br>Audit log retention policy enforced<br>Connection pooling configured | [] | App | open |
| REQ-002 | Slack Command Handler — `/coffee` | Responds within 2s with order modal<br>Modal includes drink type, size, customizations<br>Validates Slack signature<br>Publishes `slack.events` to Kafka<br>Returns 200 OK to Slack | [REQ-001] | App | open |
| REQ-003 | Order Submission Handler | Parses modal submission payload<br>Creates CoffeeRun if none active<br>Inserts Order into database<br>Publishes `coffee.orders` event<br>Updates Slack thread with order summary | [REQ-001, REQ-002] | App | open |
| REQ-004 | Runner Assignment Algorithm | Queries last 30 days of runs<br>Excludes users inactive >14 days<br>Selects user with lowest run count<br>Updates CoffeeRun.runner_user_id<br>Publishes `coffee.assignments` event | [REQ-001, REQ-003] | App | open |
| REQ-005 | Runner Notification & Reminder | Sends DM to assigned runner<br>Includes order summary and "Mark Complete" button<br>Schedules reminder after 5 minutes<br>Updates reminder_sent_at timestamp<br>Handles Slack API rate limits with retry | [REQ-004] | App | open |
| REQ-006 | Run Completion Handler | Validates runner identity<br>Updates CoffeeRun status to 'completed'<br>Publishes `coffee.completions` event<br>Posts confirmation in thread<br>Inserts AuditLog entry | [REQ-001, REQ-005] | App | open |
| REQ-007 | Slack Command Handler — `/coffee-history` | Retrieves last 10 runs from database<br>Formats response with timestamp, runner, order count<br>Responds within 2s<br>Handles empty history gracefully<br>Validates user authorization | [REQ-001] | App | open |
| REQ-008 | Slack Command Handler — `/coffee-cancel` | Validates initiator or runner identity<br>Updates CoffeeRun status to 'cancelled'<br>Publishes cancellation event<br>Notifies participants in thread<br>Inserts AuditLog entry | [REQ-001] | App | open |
| REQ-009 | User Preferences Storage | Stores last 3 orders per user<br>Updates order_count and last_ordered_at<br>Prunes preferences older than 90 days<br>Handles concurrent updates safely<br>Indexes for fast retrieval | [REQ-001, REQ-003] | App | open |
| REQ-010 | User Preferences Suggestion | Retrieves user's last order from preferences<br>Pre-fills modal with drink type and size<br>Handles missing preferences gracefully<br>Updates preferences on new order<br>Returns within 500ms | [REQ-009] | App | open |
| REQ-011 | Kafka Event Producer | Publishes events to correct topics<br>Includes correlation IDs for tracing<br>Handles broker unavailability with retry<br>Validates event schema before publish<br>Logs publish failures | [REQ-001] | App | open |
| REQ-012 | Kafka Event Consumer — Order Processing | Consumes `coffee.orders` topic<br>Triggers runner assignment after 5 min or 3 orders<br>Handles duplicate events idempotently<br>Commits offsets after processing<br>Logs processing errors | [REQ-011, REQ-004] | App | open |
| REQ-013 | Kafka Event Consumer — Audit Logging | Consumes all coffee.* topics<br>Inserts AuditLog entries<br>Handles high throughput (100 events/min)<br>Retries on database failure<br>Monitors lag and alerts | [REQ-011, REQ-001] | App | open |
| REQ-014 | REST API — Create Run | POST /api/v1/runs endpoint<br>Validates OIDC token via Kong<br>Creates CoffeeRun in database<br>Returns run_id and status<br>Rate limited to 100 req/min per user | [REQ-001] | App | open |
| REQ-015 | REST API — Add Order | POST /api/v1/runs/{run_id}/orders endpoint<br>Validates run is active<br>Inserts Order into database<br>Returns order_id<br>Publishes event to Kafka | [REQ-001, REQ-011] | App | open |
| REQ-016 | REST API — Complete Run | PATCH /api/v1/runs/{run_id}/complete endpoint<br>Validates runner authorization<br>Updates run status<br>Returns completion timestamp<br>Publishes event to Kafka | [REQ-001, REQ-011] | App | open |
| REQ-017 | Prometheus Metrics Instrumentation | Exposes /metrics endpoint<br>Tracks command latency (p50, p95, p99)<br>Tracks order volume per hour<br>Tracks error rates by endpoint<br>Tracks Kafka consumer lag | [REQ-002, REQ-011] | App | open |
| REQ-018 | Circuit Breaker for Database | Opens after 5 consecutive failures<br>Half-open after 30s cooldown<br>Returns HTTP 503 during open state<br>Logs state transitions<br>Integrates with health check endpoint | [REQ-001] | App | open |

### Acceptance — REQ-001
- PostgreSQL schema includes all entities from SPEC (User, CoffeeRun, Order, UserPreference, AuditLog)
- Foreign key constraints enforce referential integrity
- Indexes exist on `user_id`, `run_id`, `workspace_id`, `created_at` columns
- Migration scripts are idempotent (can run multiple times safely)
- Connection pool configured with max 20 connections and 30s timeout
- Audit log retention policy deletes entries older than 90 days
- Schema validation passes with sample data inserts

### Acceptance — REQ-002
- `/coffee` command responds with HTTP 200 within 2 seconds
- Response includes Slack modal with fields: drink_type (select), size (radio), customizations (text)
- Slack request signature validation passes for valid requests
- Invalid signatures return HTTP 401
- Event published to `slack.events` Kafka topic with correlation ID
- Modal trigger_id is valid for 3 seconds
- Handles concurrent requests from multiple users

### Acceptance — REQ-003
- Modal submission payload parsed correctly (drink_type, size, customizations)
- Creates new CoffeeRun if no active run exists for channel
- Inserts Order with correct run_id and user_id
- Publishes `coffee.orders` event with order details
- Updates Slack thread with formatted order summary (user, drink, size)
- Handles duplicate submissions idempotently (same user, same run)
- Returns HTTP 200 to Slack within 3 seconds

### Acceptance — REQ-004
- Queries CoffeeRun table for last 30 days filtered by workspace_id
- Excludes users with no orders in last 14 days
- Calculates run count per user and selects minimum
- Breaks ties using random selection
- Updates CoffeeRun.runner_user_id atomically
- Publishes `coffee.assignments` event with runner_user_id and run_id
- Algorithm completes within 1 second for 50 users

### Acceptance — REQ-005
- Sends Slack DM to runner within 5 seconds of assignment
- DM includes order summary (count, participants, drink types)
- DM includes "Mark Complete" interactive button
- Schedules reminder task for 5 minutes after assignment
- Reminder DM sent if run not completed
- Updates `reminder_sent_at` timestamp in database
- Handles Slack API 429 rate limit with exponential backoff (1s, 2s, 4s, max 60s)

### Acceptance — REQ-006
- Validates interaction user_id matches CoffeeRun.runner_user_id
- Returns HTTP 403 if user is not assigned runner
- Updates CoffeeRun.status to 'completed' and sets completed_at timestamp
- Publishes `coffee.completions` event to Kafka
- Posts confirmation message in original thread
- Inserts AuditLog entry with event_type='run_completed'
- Completes within 3 seconds

### Acceptance — REQ-007
- Retrieves last 10 CoffeeRun records ordered by created_at DESC
- Formats response with timestamp, runner display_name, order count
- Responds within 2 seconds
- Returns "No history found" message if no runs exist
- Validates user is member of workspace
- Handles database query timeout gracefully

### Acceptance — REQ-008
- Validates user_id is either initiator_user_id or runner_user_id
- Returns HTTP 403 if user is not authorized
- Updates CoffeeRun.status to 'cancelled'
- Publishes `coffee.run.cancelled` event to Kafka
- Posts cancellation message in thread mentioning all participants
- Inserts AuditLog entry with event_type='run_cancelled'
- Handles already completed/cancelled runs gracefully

### Acceptance — REQ-009
- Inserts UserPreference record after each order submission
- Stores drink_type, size, customizations as JSON
- Increments order_count for matching preferences
- Updates last_ordered_at timestamp
- Prunes preferences older than 90 days on daily cron
- Handles concurrent inserts with UPSERT logic
- Query retrieves preferences within 100ms

### Acceptance — REQ-010
- Retrieves user's most recent UserPreference by last_ordered_at
- Pre-fills modal drink_type and size fields
- Returns empty defaults if no preferences exist
- Updates preferences after new order submission
- Completes preference lookup within 500ms
- Handles database unavailability gracefully (returns empty defaults)

### Acceptance — REQ-011
- Publishes events to correct Kafka topics (slack.events, coffee.orders, coffee.assignments, coffee.completions)
- Includes correlation_id in event headers for tracing
- Validates event schema against JSON schema before publish
- Retries publish on broker unavailability (max 3 retries, exponential backoff)
- Logs publish failures with event payload
- Handles topic not found error gracefully
- Publishes within 100ms under normal conditions

### Acceptance — REQ-012
- Consumes messages from `coffee.orders` topic
- Triggers runner assignment after 3 orders OR 5 minutes elapsed
- Handles duplicate events using idempotency key (order_id)
- Commits Kafka offsets after successful processing
- Logs processing errors with event payload
- Consumer lag stays below 10 seconds under normal load
- Handles consumer rebalance gracefully

### Acceptance — REQ-013
- Consumes messages from all `coffee.*` topics
- Inserts AuditLog entry for each event
- Handles throughput of 100 events/min
- Retries database insert on failure (max 3 retries)
- Monitors consumer lag and alerts if >30 seconds
- Batch inserts for efficiency (batch size 10)
- Handles malformed events gracefully (logs and skips)

### Acceptance — REQ-014
- POST /api/v1/runs endpoint accepts workspace_id, channel_id, initiator_user_id
- Validates OIDC token via Kong (returns 401 if invalid)
- Creates CoffeeRun with status='active'
- Returns JSON response with run_id, status, created_at
- Rate limited to 100 req/min per user (returns 429 if exceeded)
- Handles database constraint violations (duplicate active run)
- Responds within 500ms

### Acceptance — REQ-015
- POST /api/v1/runs/{run_id}/orders endpoint accepts user_id, drink_type, size, customizations
- Validates run_id exists and status='active' (returns 404 if not found, 400 if not active)
- Inserts Order into database
- Returns JSON response with order_id, created_at
- Publishes `coffee.orders` event to Kafka
- Handles concurrent order submissions safely
- Responds within 500ms

### Acceptance — REQ-016
- PATCH /api/v1/runs/{run_id}/complete endpoint validates runner authorization
- Returns 403 if user_id does not match runner_user_id
- Updates CoffeeRun.status to 'completed' and sets completed_at
- Returns JSON response with completion timestamp
- Publishes `coffee.completions` event to Kafka
- Handles already completed runs (returns 400)
- Responds within 500ms

### Acceptance — REQ-017
- Exposes /metrics endpoint in Prometheus format
- Tracks `http_request_duration_seconds` histogram with p50, p95, p99 quantiles
- Tracks `coffee_orders_total` counter by workspace_id
- Tracks `http_request_errors_total` counter by endpoint and status_code
- Tracks `kafka_consumer_lag_seconds` gauge by topic
- Metrics updated in real-time (no batching delay)
- Prometheus scrape completes within 1 second

### Acceptance — REQ-018
- Circuit breaker opens after 5 consecutive database connection failures
- Returns HTTP 503 with "Service Unavailable" message during open state
- Transitions to half-open after 30 seconds cooldown
- Closes after 1 successful database query in half-open state
- Logs state transitions (closed -> open -> half-open -> closed)
- Integrates with /health endpoint (returns unhealthy during open state)
- Handles concurrent requests during state transitions safely

## Dependency Graph (textual)

```
REQ-001 -> (no dependencies)
REQ-002 -> REQ-001
REQ-003 -> REQ-001, REQ-002
REQ-004 -> REQ-001, REQ-003
REQ-005 -> REQ-004
REQ-006 -> REQ-001, REQ-005
REQ-007 -> REQ-001
REQ-008 -> REQ-001
REQ-009 -> REQ-001, REQ-003
REQ-010 -> REQ-009
REQ-011 -> REQ-001
REQ-012 -> REQ-011, REQ-004
REQ-013 -> REQ-011, REQ-001
REQ-014 -> REQ-001
REQ-015 -> REQ-001, REQ-011
REQ-016 -> REQ-001, REQ-011
REQ-017 -> REQ-002, REQ-011
REQ-018 -> REQ-001
```

## Iteration Strategy

**Batch 1 (Foundation):** REQ-001, REQ-011, REQ-018
- Estimation: Medium (3-5 days)
- Establishes database schema, Kafka integration, resilience patterns
- Confidence: High (±0 batches)

**Batch 2 (Core Commands):** REQ-002, REQ-003, REQ-014, REQ-015
- Estimation: Large (5-7 days)
- Implements `/coffee` command, order submission, REST API
- Confidence: Medium (±1 batch)

**Batch 3 (Runner Assignment):** REQ-004, REQ-005, REQ-012
- Estimation: Medium (3-5 days)
- Implements fairness algorithm, notifications, event processing
- Confidence: High (±0 batches)

**Batch 4 (Completion & History):** REQ-006, REQ-007, REQ-008, REQ-016
- Estimation: Medium (3-5 days)
- Implements run completion, history, cancellation
- Confidence: High (±0 batches)

**Batch 5 (Preferences & Observability):** REQ-009, REQ-010, REQ-013, REQ-017
- Estimation: Medium (3-5 days)
- Implements user preferences, audit logging, metrics
- Confidence: Medium (±1 batch)

**Total Estimation:** 17-27 days (3.5-5.5 weeks)

## Test Strategy

**Per REQ:**
- **Unit Tests:** Business logic (runner assignment algorithm, preference storage, circuit breaker state machine)
- **Integration Tests:** Database queries, Kafka publish/consume, Slack API mocking
- **Contract Tests:** REST API request/response validation, Kafka event schema validation

**Per Batch:**
- **End-to-End Tests:** Full workflow from `/coffee` command to run completion
- **Load Tests:** 50 concurrent users, 100 orders/day, Kafka throughput
- **Resilience Tests:** Database failure, Kafka broker failure, Slack API rate limits

**Acceptance Validation:**
- Each REQ's acceptance criteria mapped to automated test cases
- Minimum 80% code coverage for business logic
- All E2E tests pass before batch completion

## KIT Readiness (per REQ)

**REQ-001 (Database Schema):**
- Path: `/runs/kit/REQ-001/src/migrations/001_initial_schema.sql`
- Path: `/runs/kit/REQ-001/test/test_schema_validation.py`
- Scaffolds: Alembic migration, pytest fixtures for database setup
- Commands: `alembic upgrade head`, `pytest test/test_schema_validation.py`
- Expected: Migration applies cleanly, all tables created, indexes verified
- **KIT-functional: yes**

**REQ-002 (Slack Command Handler):**
- Path: `/runs/kit/REQ-002/src/handlers/coffee_command.py`
- Path: `/runs/kit/REQ-002/test/test_coffee_command.py`
- Scaffolds: FastAPI route, Slack signature validation, Kafka producer mock
- Commands: `pytest test/test_coffee_command.py`, `uvicorn app:app --reload`
- Expected: Tests pass, modal response validated, signature check works
- **KIT-functional: yes**

**REQ-003 (Order Submission):**
- Path: `/runs/kit/REQ-003/src/handlers/order_submission.py`
- Path: `/runs/kit/REQ-003/test/test_order_submission.py`
- Scaffolds: Modal payload parser, database insert, Kafka event publisher
- Commands: `pytest test/test_order_submission.py`
- Expected: Order inserted, event published, thread updated
- **KIT-functional: yes**

**REQ-004 (Runner Assignment):**
- Path: `/runs/kit/REQ-004/src/services/runner_assignment.py`
- Path: `/runs/kit/REQ-004/test/test_runner_assignment.py`
- Scaffolds: Fairness algorithm, database query, event publisher
- Commands: `pytest test/test_runner_assignment.py`
- Expected: Correct runner selected, ties broken randomly, event published
- **KIT-functional: yes**

**REQ-005 (Runner Notification):**
- Path: `/runs/kit/REQ-005/src/services/runner_notification.py`
- Path: `/runs/kit/REQ-005/test/test_runner_notification.py`
- Scaffolds: Slack DM sender, reminder scheduler, retry logic
- Commands: `pytest test/test_runner_notification.py`
- Expected: DM sent, reminder scheduled, rate limit handled
- **KIT-functional: yes**

**REQ-006 (Run Completion):**
- Path: `/runs/kit/REQ-006/src/handlers/run_completion.py`
- Path: `/runs/kit/REQ-006/test/test_run_completion.py`
- Scaffolds: Authorization check, database update, event publisher
- Commands: `pytest test/test_run_completion.py`
- Expected: Status updated, event published, audit log inserted
- **KIT-functional: yes**

**REQ-007 (Coffee History):**
- Path: `/runs/kit/REQ-007/src/handlers/coffee_history.py`
- Path: `/runs/kit/REQ-007/test/test_coffee_history.py`
- Scaffolds: Database query, response formatter
- Commands: `pytest test/test_coffee_history.py`
- Expected: Last 10 runs retrieved, formatted correctly
- **KIT-functional: yes**

**REQ-008 (Coffee Cancel):**
- Path: `/runs/kit/REQ-008/src/handlers/coffee_cancel.py`
- Path: `/runs/kit/REQ-008/test/test_coffee_cancel.py`
- Scaffolds: Authorization check, database update, event publisher
- Commands: `pytest test/test_coffee_cancel.py`
- Expected: Status updated, participants notified, audit log inserted
- **KIT-functional: yes**

**REQ-009 (User Preferences Storage):**
- Path: `/runs/kit/REQ-009/src/services/user_preferences.py`
- Path: `/runs/kit/REQ-009/test/test_user_preferences.py`
- Scaffolds: UPSERT logic, pruning cron job
- Commands: `pytest test/test_user_preferences.py`
- Expected: Preferences stored, order_count incremented, old records pruned
- **KIT-functional: yes**

**REQ-010 (User Preferences Suggestion):**
- Path: `/runs/kit/REQ-010/src/services/preference_suggestion.py`
- Path: `/runs/kit/REQ-010/test/test_preference_suggestion.py`
- Scaffolds: Database query, modal pre-fill logic
- Commands: `pytest test/test_preference_suggestion.py`
- Expected: Last preference retrieved, modal pre-filled, empty defaults handled
- **KIT-functional: yes**

**REQ-011 (Kafka Event Producer):**
- Path: `/runs/kit/REQ-011/src/services/kafka_producer.py`
- Path: `/runs/kit/REQ-011/test/test_kafka_producer.py`
- Scaffolds: Kafka client wrapper, schema validation, retry logic
- Commands: `pytest test/test_kafka_producer.py`
- Expected: Events published, schema validated, retries work
- **KIT-functional: yes**

**REQ-012 (Kafka Event Consumer — Order Processing):**
- Path: `/runs/kit/REQ-012/src/consumers/order_consumer.py`
- Path: `/runs/kit/REQ-012/test/test_order_consumer.py`
- Scaffolds: Kafka consumer, idempotency check, offset commit
- Commands: `pytest test/test_order_consumer.py`
- Expected: Events consumed, runner assigned, offsets committed
- **KIT-functional: yes**

**REQ-013 (Kafka Event Consumer — Audit Logging):**
- Path: `/runs/kit/REQ-013/src/consumers/audit_consumer.py`
- Path: `/runs/kit/REQ-013/test/test_audit_consumer.py`
- Scaffolds: Kafka consumer, batch insert, lag monitoring
- Commands: `pytest test/test_audit_consumer.py`
- Expected: Audit logs inserted, batch processing works, lag monitored
- **KIT-functional: yes**

**REQ-014 (REST API — Create Run):**
- Path: `/runs/kit/REQ-014/src/api/runs.py`
- Path: `/runs/kit/REQ-014/test/test_api_runs.py`
- Scaffolds: FastAPI route, OIDC validation, rate limiting
- Commands: `pytest test/test_api_runs.py`
- Expected: Run created, rate limit enforced, OIDC validated
- **KIT-functional: yes**

**REQ-015 (REST API — Add Order):**
- Path: `/runs/kit/REQ-015/src/api/orders.py`
- Path: `/runs/kit/REQ-015/test/test_api_orders.py`
- Scaffolds: FastAPI route, validation, event publisher
- Commands: `pytest test/test_api_orders.py`
- Expected: Order inserted, event published, validation works
- **KIT-functional: yes**

**REQ-016 (REST API — Complete Run):**
- Path: `/runs/kit/REQ-016/src/api/complete.py`
- Path: `/runs/kit/REQ-016/test/test_api_complete.py`
- Scaffolds: FastAPI route, authorization, event publisher
- Commands: `pytest test/test_api_complete.py`
- Expected: Run completed, authorization enforced, event published
- **KIT-functional: yes**

**REQ-017 (Prometheus Metrics):**
- Path: `/runs/kit/REQ-017/src/observability/metrics.py`
- Path: `/runs/kit/REQ-017/test/test_metrics.py`
- Scaffolds: Prometheus client, middleware, /metrics endpoint
- Commands: `pytest test/test_metrics.py`, `curl http://localhost:8000/metrics`
- Expected: Metrics exposed, histograms/counters updated, scrape works
- **KIT-functional: yes**

**REQ-018 (Circuit Breaker):**
- Path: `/runs/kit/REQ-018/src/resilience/circuit_breaker.py`
- Path: `/runs/kit/REQ-018/test/test_circuit_breaker.py`
- Scaffolds: Circuit breaker state machine, health check integration
- Commands: `pytest test/test_circuit_breaker.py`
- Expected: State transitions work, HTTP 503 during open, health check reflects state
- **KIT-functional: yes**

## Notes

**Assumptions:**
- Slack Enterprise Grid is approved and accessible from corporate network
- Ory Hydra/Kratos is pre-deployed and service accounts can be created
- Kafka cluster has 3+ brokers with replication factor 2
- PostgreSQL persistent volumes are provisioned in Kubernetes
- Kong Gateway is configured with OIDC plugin for token validation
- Hashicorp Vault is accessible via Kubernetes service account

**Risks & Mitigations:**
- **Risk:** Slack API rate limits (50 req/min) cause delays
  - **Mitigation:** Kafka buffering, exponential backoff, batch sends (REQ-011, REQ-005)
- **Risk:** Database connection pool exhaustion under load
  - **Mitigation:** Connection pooling (max 20), circuit breaker (REQ-018), horizontal scaling
- **Risk:** Unfair runner assignment with frequent team changes
  - **Mitigation:** 30-day activity window, exclude inactive users (REQ-004)
- **Risk:** Secrets leaked in logs
  - **Mitigation:** Log sanitization, Vault audit logs, no plaintext credentials

**Technology Choices:**
- **Python 3.11+** with FastAPI for REST API and Slack handlers
- **SQLAlchemy 2.0** for database ORM (Pydantic v2 compatible)
- **Alembic** for database migrations
- **aiokafka** for async Kafka producer/consumer
- **httpx** for async Slack API calls
- **prometheus-client** for metrics instrumentation
- **pytest** with pytest-asyncio for testing
- **Docker** for containerization, Helm for Kubernetes deployment

**Lane Detection:**
- Detected lanes: `python`, `sql`, `kafka`, `ci`, `infra`
- Lane guides emitted for each detected lane (see separate files)
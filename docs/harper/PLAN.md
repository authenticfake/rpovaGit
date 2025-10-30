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
- **Infra Track:** Kubernetes deployment, Kong Gateway configuration, Ory Hydra/Kratos integration, Vault secrets injection, Prometheus/Grafana observability setup

**Scope Boundaries:**
- **In Scope:** Slack command handlers, order management, runner assignment fairness algorithm, Kafka event producers/consumers, PostgreSQL schema and queries, OIDC token validation, metrics instrumentation
- **Out of Scope:** Payment processing, external delivery APIs, mobile apps, GPS tracking, multi-tenant SaaS, ML-based predictions, calendar integrations

**Deferred to Infra Track:**
- Kubernetes Helm chart creation and deployment
- Kong Gateway route configuration and OIDC plugin setup
- Ory Hydra/Kratos service account provisioning
- Vault secret injection via Kubernetes service account
- Prometheus scrape configuration and Grafana dashboard creation
- CI/CD Jenkins pipeline setup

## REQ-IDs Table

| ID | Title | Acceptance (bullets) | DependsOn [IDs] | Track | Status |
|----|-------|---------------------|-----------------|-------|--------|
| REQ-001 | PostgreSQL Schema Definition | Schema creates all tables<br>Indexes on foreign keys exist<br>ENUM types defined correctly<br>Timestamps default to NOW()<br>UUIDs use gen_random_uuid() | [] | App | open |
| REQ-002 | Database Connection Pool | Pool initializes with max 20 connections<br>Connection timeout set to 5s<br>Health check query executes on startup<br>Graceful shutdown closes all connections<br>Metrics expose active/idle connection counts | [REQ-001] | App | open |
| REQ-003 | Vault Secrets Client | Client authenticates via Kubernetes service account<br>Fetches Slack signing secret successfully<br>Fetches PostgreSQL credentials successfully<br>Caches secrets for 5 minutes<br>Retries with exponential backoff on failure | [] | App | open |
| REQ-004 | Slack Signature Verification Middleware | Middleware validates X-Slack-Signature header<br>Rejects requests with invalid signatures (401)<br>Rejects requests older than 5 minutes (401)<br>Logs verification failures to Prometheus<br>Passes valid requests to handler | [REQ-003] | App | open |
| REQ-005 | Slack Command Handler — /coffee | Responds within 2 seconds with modal payload<br>Modal includes drink_type dropdown (5 options)<br>Modal includes size radio buttons (3 options)<br>Modal includes customizations text input<br>Returns HTTP 200 with application/json | [REQ-004] | App | open |
| REQ-006 | Slack Interaction Handler — Order Submission | Parses modal submission payload<br>Creates CoffeeRun record if first order<br>Inserts Order record with user_id and run_id<br>Publishes coffee.order.placed event to Kafka<br>Returns HTTP 200 with thread update message | [REQ-002, REQ-004, REQ-007] | App | open |
| REQ-007 | Kafka Producer — Event Publishing | Producer initializes with 3 partition topic<br>Publishes events with user_id as partition key<br>Confirms delivery with acks=all<br>Retries up to 3 times on failure<br>Logs publish failures to Prometheus | [] | App | open |
| REQ-008 | Runner Assignment Algorithm | Queries last 30 days of runs per user<br>Excludes users with no orders in 14 days<br>Selects user with minimum run count<br>Breaks ties by earliest last_run timestamp<br>Updates CoffeeRun.runner_user_id atomically | [REQ-002] | App | open |
| REQ-009 | Kafka Consumer — Runner Assignment Trigger | Consumes coffee.order.placed events<br>Triggers assignment after 5-minute window or 5 orders<br>Calls runner assignment algorithm<br>Publishes coffee.runner.assigned event<br>Commits offset after successful processing | [REQ-007, REQ-008] | App | open |
| REQ-010 | Slack Messaging Client — DM Sender | Sends DM via chat.postMessage API<br>Includes order summary with markdown formatting<br>Attaches "Mark Complete" button with callback_id<br>Retries with exponential backoff on HTTP 429<br>Logs rate limit events to Prometheus | [REQ-003] | App | open |
| REQ-011 | Reminder Scheduler — Runner Notification | Schedules reminder 5 minutes after assignment<br>Fetches runner_user_id from CoffeeRun<br>Calls Slack DM sender with reminder message<br>Updates reminder_sent_at timestamp<br>Handles cancellation if run completed early | [REQ-002, REQ-010] | App | open |
| REQ-012 | Slack Interaction Handler — Mark Complete | Parses button click payload<br>Validates runner_user_id matches clicker<br>Updates CoffeeRun status to completed<br>Publishes coffee.run.completed event<br>Posts completion message in thread | [REQ-002, REQ-004, REQ-007] | App | open |
| REQ-013 | User Preferences — Storage and Retrieval | Inserts/updates UserPreference on order placement<br>Increments order_count for matching preferences<br>Retrieves top 3 preferences by order_count<br>Returns preferences sorted by last_ordered_at<br>Handles missing preferences gracefully | [REQ-002] | App | open |
| REQ-014 | Slack Command Handler — /coffee-history | Queries last 10 CoffeeRun records for user<br>Joins with Order to get order counts<br>Formats response with timestamps and runner names<br>Returns HTTP 200 within 2 seconds<br>Handles empty history with friendly message | [REQ-002, REQ-004] | App | open |
| REQ-015 | Slack Command Handler — /coffee-cancel | Validates user is initiator or runner<br>Updates CoffeeRun status to cancelled<br>Publishes coffee.run.cancelled event<br>Posts cancellation message in thread<br>Returns HTTP 403 if unauthorized | [REQ-002, REQ-004, REQ-007] | App | open |
| REQ-016 | Audit Logging — Event Persistence | Inserts AuditLog record for each event type<br>Stores event_type, user_id, run_id, payload<br>Payload serialized as JSONB<br>Timestamp defaults to NOW()<br>Retention policy enforced via cron job (90 days) | [REQ-002] | App | open |
| REQ-017 | Prometheus Metrics Instrumentation | Exposes /metrics endpoint with histogram for command latency<br>Counter for order placements by drink_type<br>Gauge for active runs<br>Counter for runner assignments<br>Counter for errors by type | [] | App | open |
| REQ-018 | Circuit Breaker — PostgreSQL Resilience | Opens after 5 consecutive connection failures<br>Half-opens after 30 seconds<br>Returns HTTP 503 during open state<br>Logs state transitions to Prometheus<br>Recovers automatically when database available | [REQ-002] | App | open |

### Acceptance — REQ-001
- Schema migration script creates `users`, `coffee_runs`, `orders`, `user_preferences`, `audit_logs` tables
- Foreign key constraints exist on `coffee_runs.initiator_user_id`, `coffee_runs.runner_user_id`, `orders.run_id`, `orders.user_id`
- Indexes created on `coffee_runs.workspace_id`, `coffee_runs.status`, `orders.run_id`, `user_preferences.user_id`
- ENUM type `run_status` defined with values `active`, `completed`, `cancelled`
- All timestamp columns default to `NOW()` and UUID columns use `gen_random_uuid()`

### Acceptance — REQ-002
- Connection pool initializes with `max_connections=20`, `min_connections=5`, `timeout=5s`
- Health check query `SELECT 1` executes successfully on application startup
- Graceful shutdown waits up to 10 seconds for active queries before closing connections
- Prometheus metrics `db_connections_active` and `db_connections_idle` exposed
- Connection acquisition failures logged with error details

### Acceptance — REQ-003
- Client authenticates to Vault using Kubernetes service account token from `/var/run/secrets/kubernetes.io/serviceaccount/token`
- Fetches `slack/signing_secret` from Vault path `secret/coffeebuddy/slack`
- Fetches `postgres/username` and `postgres/password` from Vault path `secret/coffeebuddy/db`
- Secrets cached in memory for 5 minutes with TTL refresh
- Retries with exponential backoff (1s, 2s, 4s, 8s) on HTTP 5xx errors

### Acceptance — REQ-004
- Middleware extracts `X-Slack-Signature` and `X-Slack-Request-Timestamp` headers
- Computes HMAC-SHA256 signature using signing secret and request body
- Rejects requests with mismatched signatures (HTTP 401, body: `{"error": "invalid_signature"}`)
- Rejects requests with timestamps older than 5 minutes (HTTP 401, body: `{"error": "request_expired"}`)
- Prometheus counter `slack_signature_verification_failures_total` incremented on rejection

### Acceptance — REQ-005
- Handler responds within 2 seconds with HTTP 200 and `Content-Type: application/json`
- Response body contains `type: modal`, `callback_id: coffee_order_modal`
- Modal includes `drink_type` select input with options: `Latte`, `Espresso`, `Cappuccino`, `Americano`, `Mocha`
- Modal includes `size` radio buttons with options: `Small`, `Medium`, `Large`
- Modal includes `customizations` plain text input with placeholder `Extra shot, oat milk, etc.`

### Acceptance — REQ-006
- Parses `view.state.values` from Slack modal submission payload
- Creates `CoffeeRun` record with `status=active` if no active run exists for channel
- Inserts `Order` record with `user_id`, `run_id`, `drink_type`, `size`, `customizations`
- Publishes event to Kafka topic `coffee.orders` with schema `{event_type, user_id, run_id, order_id, timestamp}`
- Returns HTTP 200 with `response_action: update`, message text includes order summary

### Acceptance — REQ-007
- Producer initializes with `bootstrap.servers` from environment variable `KAFKA_BROKERS`
- Publishes events to topics `coffee.orders`, `coffee.assignments`, `coffee.completions` with `acks=all`
- Uses `user_id` as partition key for consistent ordering per user
- Retries up to 3 times with 1-second delay on transient failures
- Prometheus counter `kafka_publish_failures_total` incremented on exhausted retries

### Acceptance — REQ-008
- Queries `coffee_runs` table for runs created in last 30 days, grouped by `runner_user_id`
- Excludes users with no `orders` in last 14 days (subquery on `orders.created_at`)
- Selects user with minimum `COUNT(run_id)` as runner
- Breaks ties by selecting user with earliest `MAX(created_at)` (last run timestamp)
- Updates `CoffeeRun.runner_user_id` using `UPDATE ... WHERE run_id = ? AND runner_user_id IS NULL` (atomic)

### Acceptance — REQ-009
- Consumer subscribes to Kafka topic `coffee.orders` with `group.id=runner-assignment-consumer`
- Buffers events for 5 minutes or until 5 orders received for same `run_id`
- Calls runner assignment algorithm (REQ-008) after buffer threshold met
- Publishes `coffee.runner.assigned` event with schema `{event_type, run_id, runner_user_id, timestamp}`
- Commits Kafka offset only after successful database update and event publish

### Acceptance — REQ-010
- Calls Slack API `chat.postMessage` with `channel=<user_id>` (DM), `text=<order_summary>`
- Message includes markdown-formatted order list with drink types and customizations
- Attaches interactive button with `action_id: mark_complete`, `value: <run_id>`
- Retries with exponential backoff (1s, 2s, 4s, 8s, 16s) on HTTP 429 (rate limit)
- Prometheus counter `slack_rate_limit_events_total` incremented on HTTP 429

### Acceptance — REQ-011
- Schedules reminder task 5 minutes after `coffee.runner.assigned` event timestamp
- Fetches `runner_user_id` from `CoffeeRun` table using `run_id`
- Calls Slack DM sender (REQ-010) with message text `Reminder: You're the runner for coffee run <run_id>`
- Updates `CoffeeRun.reminder_sent_at` timestamp after successful send
- Cancels scheduled task if `CoffeeRun.status` changes to `completed` or `cancelled` before 5 minutes

### Acceptance — REQ-012
- Parses `actions[0].value` from Slack interaction payload to extract `run_id`
- Validates `user.id` from payload matches `CoffeeRun.runner_user_id` (returns HTTP 403 if mismatch)
- Updates `CoffeeRun` with `status=completed`, `completed_at=NOW()` using `UPDATE ... WHERE run_id = ? AND status = 'active'`
- Publishes `coffee.run.completed` event with schema `{event_type, run_id, runner_user_id, timestamp}`
- Posts message in original thread with text `Coffee run completed by <@runner_user_id>!`

### Acceptance — REQ-013
- Inserts `UserPreference` record on order placement if no matching `(user_id, drink_type, size)` exists
- Updates `order_count` and `last_ordered_at` if matching preference exists (using `ON CONFLICT ... DO UPDATE`)
- Retrieves top 3 preferences ordered by `order_count DESC, last_ordered_at DESC`
- Returns preferences as JSON array `[{drink_type, size, customizations, order_count}]`
- Returns empty array `[]` if no preferences exist for user

### Acceptance — REQ-014
- Queries `coffee_runs` table with `WHERE initiator_user_id = ? OR runner_user_id = ?` and `ORDER BY created_at DESC LIMIT 10`
- Joins with `orders` table to count orders per run (`COUNT(order_id) AS order_count`)
- Formats response as Slack message with blocks: `[{timestamp, runner_name, order_count}]`
- Returns HTTP 200 within 2 seconds (measured by Prometheus histogram `command_latency_seconds`)
- Returns message `No coffee runs found` if query result is empty

### Acceptance — REQ-015
- Validates `user_id` from Slack payload matches `CoffeeRun.initiator_user_id` OR `CoffeeRun.runner_user_id`
- Returns HTTP 403 with body `{"error": "unauthorized"}` if validation fails
- Updates `CoffeeRun` with `status=cancelled` using `UPDATE ... WHERE run_id = ? AND status = 'active'`
- Publishes `coffee.run.cancelled` event with schema `{event_type, run_id, cancelled_by_user_id, timestamp}`
- Posts message in thread with text `Coffee run cancelled by <@user_id>`

### Acceptance — REQ-016
- Inserts `AuditLog` record for event types: `order_placed`, `runner_assigned`, `run_completed`, `run_cancelled`
- Stores `event_type` as VARCHAR(50), `user_id` as VARCHAR(64), `run_id` as UUID, `payload` as JSONB
- Payload includes full event details (e.g., `{drink_type, size, customizations}` for `order_placed`)
- Timestamp defaults to `NOW()` on insert
- Cron job deletes records older than 90 days (`DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days'`)

### Acceptance — REQ-017
- Exposes `/metrics` endpoint returning Prometheus text format
- Histogram `command_latency_seconds` with buckets `[0.1, 0.5, 1.0, 2.0, 5.0]` for `/coffee`, `/coffee-history`, `/coffee-cancel`
- Counter `orders_total` with label `drink_type` incremented on order placement
- Gauge `active_runs` reflecting current count of `CoffeeRun` records with `status=active`
- Counter `errors_total` with label `error_type` incremented on exceptions

### Acceptance — REQ-018
- Circuit breaker opens after 5 consecutive PostgreSQL connection failures (tracked in-memory)
- Half-opens after 30 seconds, allowing 1 test query (`SELECT 1`)
- Returns HTTP 503 with body `{"error": "service_unavailable"}` during open state
- Prometheus gauge `circuit_breaker_state` with values `0=closed, 1=open, 2=half_open`
- Closes circuit breaker after successful test query in half-open state

## Dependency Graph (textual)

```
REQ-002 -> REQ-001
REQ-004 -> REQ-003
REQ-006 -> REQ-002, REQ-004, REQ-007
REQ-009 -> REQ-007, REQ-008
REQ-008 -> REQ-002
REQ-010 -> REQ-003
REQ-011 -> REQ-002, REQ-010
REQ-012 -> REQ-002, REQ-004, REQ-007
REQ-013 -> REQ-002
REQ-014 -> REQ-002, REQ-004
REQ-015 -> REQ-002, REQ-004, REQ-007
REQ-016 -> REQ-002
REQ-018 -> REQ-002
```

**Critical Path:**
REQ-001 → REQ-002 → REQ-008 → REQ-009 (runner assignment flow)
REQ-003 → REQ-004 → REQ-005 (Slack command entry point)

## Iteration Strategy

**Batch 1 (Foundation):** REQ-001, REQ-002, REQ-003, REQ-007, REQ-017
- **Estimation:** Medium (3-5 sessions)
- **Goal:** Database schema, connection pooling, secrets management, Kafka producer, metrics endpoint
- **Confidence:** High (±0 batches) — foundational components with clear contracts

**Batch 2 (Slack Integration):** REQ-004, REQ-005, REQ-010
- **Estimation:** Small (2-3 sessions)
- **Goal:** Slack signature verification, `/coffee` command handler, DM sender
- **Confidence:** High (±0 batches) — well-defined Slack API interactions

**Batch 3 (Order Flow):** REQ-006, REQ-013, REQ-016
- **Estimation:** Medium (3-4 sessions)
- **Goal:** Order submission, user preferences, audit logging
- **Confidence:** Medium (±1 batch) — depends on Kafka producer stability

**Batch 4 (Runner Assignment):** REQ-008, REQ-009, REQ-011
- **Estimation:** Large (4-6 sessions)
- **Goal:** Fairness algorithm, Kafka consumer, reminder scheduler
- **Confidence:** Medium (±1 batch) — complex fairness logic and timing

**Batch 5 (Completion & History):** REQ-012, REQ-014, REQ-015
- **Estimation:** Small (2-3 sessions)
- **Goal:** Mark complete handler, history command, cancel command
- **Confidence:** High (±0 batches) — straightforward CRUD operations

**Batch 6 (Resilience):** REQ-018
- **Estimation:** Small (1-2 sessions)
- **Goal:** Circuit breaker for PostgreSQL
- **Confidence:** High (±0 batches) — isolated resilience pattern

## Test Strategy

**Per REQ:**
- **Unit Tests:** Mock external dependencies (Slack API, Kafka, PostgreSQL, Vault); verify business logic in isolation
- **Integration Tests:** Use Testcontainers for PostgreSQL and Kafka; verify end-to-end flows within service boundary
- **Contract Tests:** Validate Slack API request/response schemas using recorded fixtures

**Per Batch:**
- **Batch 1:** Verify schema migrations apply cleanly; connection pool metrics accurate; Vault secrets fetched; Kafka producer publishes events
- **Batch 2:** Verify Slack signature validation rejects invalid requests; `/coffee` modal renders correctly; DM sender retries on rate limit
- **Batch 3:** Verify order submission creates records; preferences stored and retrieved; audit logs persisted
- **Batch 4:** Verify fairness algorithm selects correct runner; Kafka consumer triggers assignment; reminders sent on schedule
- **Batch 5:** Verify mark complete updates status; history command returns last 10 runs; cancel command rejects unauthorized users
- **Batch 6:** Verify circuit breaker opens after failures; half-opens after timeout; returns 503 during open state

**End-to-End (E2E):**
- Simulate full coffee run: `/coffee` → order submission → runner assignment → reminder → mark complete
- Verify Kafka events published in correct order
- Verify audit logs contain all events
- Verify Prometheus metrics reflect activity

## KIT Readiness (per REQ)

**All REQs are KIT-ready** with the following structure:

**Paths:**
- `/runs/kit/<REQ-ID>/src` — Implementation code (Python modules)
- `/runs/kit/<REQ-ID>/test` — Test code (pytest fixtures and test cases)

**Scaffolds:**
- `src/main.py` — FastAPI application entry point
- `src/handlers/` — Slack command and interaction handlers
- `src/services/` — Business logic (runner assignment, preferences)
- `src/clients/` — External clients (Slack, Kafka, PostgreSQL, Vault)
- `src/models/` — Pydantic models for request/response schemas
- `test/conftest.py` — Pytest fixtures (mock clients, Testcontainers)
- `test/unit/` — Unit tests for services and handlers
- `test/integration/` — Integration tests with real PostgreSQL/Kafka

**Commands:**
- `pytest test/unit` — Run unit tests (fast, no external dependencies)
- `pytest test/integration` — Run integration tests (requires Testcontainers)
- `pytest --cov=src --cov-report=term-missing` — Generate coverage report

**Expected Pass/Fail:**
- Unit tests: 100% pass (mocked dependencies)
- Integration tests: 100% pass (Testcontainers provide real services)
- Coverage: ≥80% line coverage per REQ

**KIT-functional: yes** for all REQs — each REQ is independently testable with clear acceptance criteria and mocked/containerized dependencies.

## Notes

**Assumptions:**
- Python 3.11+ runtime with FastAPI 0.104+, Pydantic v2, asyncpg for PostgreSQL, aiokafka for Kafka
- Slack API uses current stable endpoints (no deprecated methods)
- Ory Hydra/Kratos OIDC tokens include `sub` (user ID) and `email` claims
- Kafka topics pre-created with 3 partitions and replication factor 2
- PostgreSQL 15+ with `gen_random_uuid()` extension enabled

**Risks & Mitigations:**
- **Risk:** Slack API rate limits (50 req/min) cause message delivery delays
  - **Mitigation:** Kafka buffering (REQ-007, REQ-009); exponential backoff in DM sender (REQ-010)
- **Risk:** Fairness algorithm unfair if users join/leave frequently
  - **Mitigation:** 30-day lookback window; exclude inactive users (REQ-008)
- **Risk:** Database connection pool exhaustion under high load
  - **Mitigation:** Max 20 connections; circuit breaker (REQ-018); horizontal scaling of app replicas

**Technology Choices:**
- **FastAPI:** Modern async Python framework with OpenAPI support
- **asyncpg:** High-performance async PostgreSQL driver
- **aiokafka:** Async Kafka client for Python
- **hvac:** HashiCorp Vault client for Python
- **pytest + Testcontainers:** Test framework with containerized dependencies
- **prometheus_client:** Prometheus metrics instrumentation

**Infra Track (Deferred):**
- Kubernetes Helm chart with Deployment, Service, ConfigMap, Secret resources
- Kong Gateway configuration with OIDC plugin and route definitions
- Ory Hydra/Kratos service account creation and token issuance
- Vault policy for CoffeeBuddy service account
- Prometheus ServiceMonitor for metrics scraping
- Grafana dashboard JSON for command latency, order volume, error rates
- Jenkins pipeline for build, test, Docker image push, Helm deploy
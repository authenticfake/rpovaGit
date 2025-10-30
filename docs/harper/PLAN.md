# PLAN — CoffeeBuddy (On-Prem)

## Plan Snapshot
- **Counts:** 18 total / 18 open / 0 done / 0 deferred
- **Progress:** 0% complete (0 / 18)
- **Checklist:**
  - [x] SPEC aligned
  - [x] Prior REQ reconciled (no prior plan exists)
  - [x] Dependencies mapped
  - [x] KIT-readiness per REQ confirmed

## Tracks & Scope Boundaries

**Tracks:**
- **App Track:** Core business logic, Slack integration, API endpoints, event processing, runner assignment algorithm, user preferences, audit logging (REQ-001 through REQ-012)
- **Infra Track:** Kubernetes deployment, Kong Gateway configuration, Vault integration, Kafka topic setup, PostgreSQL schema deployment, monitoring stack (REQ-013 through REQ-018)

**Scope Boundaries:**
- **In Scope:** Slack command handlers, runner fairness algorithm, event-driven architecture, OIDC authentication, on-prem deployment
- **Out of Scope:** Payment processing, external delivery APIs, mobile apps, GPS tracking, multi-tenant SaaS, ML-based predictions, calendar integration
- **Deferred:** Advanced analytics dashboards, automated run scheduling, order editing in threads

## REQ-IDs Table

| ID | Title | Acceptance (bullets) | DependsOn [IDs] | Track | Status |
|----|-------|---------------------|-----------------|-------|--------|
| REQ-001 | Slack Command Handler Foundation | FastAPI endpoint accepts POST /slack/commands<br>Validates Slack signature using signing secret<br>Returns 200 with ephemeral message within 2s<br>Logs command metadata to structured JSON<br>Handles /coffee, /coffee-history, /coffee-cancel commands | [] | App | open |
| REQ-002 | Order Submission Modal | Opens Slack modal with drink type, size, customization fields<br>Validates modal submission payload<br>Persists order to PostgreSQL orders table<br>Publishes coffee.order.placed event to Kafka<br>Returns confirmation message to user within 5s | [REQ-001] | App | open |
| REQ-003 | Coffee Run Lifecycle Management | Creates CoffeeRun entity with status=active<br>Generates UUID for run_id<br>Associates run with workspace_id and channel_id<br>Stores initiator_user_id from Slack payload<br>Publishes coffee.run.created event to Kafka | [REQ-001] | App | open |
| REQ-004 | Runner Assignment Algorithm | Queries last 30 days of runs per user<br>Calculates weighted fairness score (fewest runs wins)<br>Excludes users with no orders in 14 days<br>Updates CoffeeRun.runner_user_id atomically<br>Publishes coffee.runner.assigned event to Kafka | [REQ-003] | App | open |
| REQ-005 | Runner Notification System | Sends Slack DM to assigned runner within 5 minutes<br>Includes order summary with drink types and sizes<br>Attaches "Mark Complete" interactive button<br>Updates reminder_sent_at timestamp in PostgreSQL<br>Retries with exponential backoff on Slack API failure | [REQ-004] | App | open |
| REQ-006 | Run Completion Handler | Validates button interaction from assigned runner<br>Updates CoffeeRun status to completed<br>Records completed_at timestamp<br>Publishes coffee.run.completed event to Kafka<br>Posts completion message in original thread | [REQ-005] | App | open |
| REQ-007 | User Preference Tracking | Stores last 3 orders per user in UserPreference table<br>Increments order_count for each drink type<br>Updates last_ordered_at timestamp<br>Suggests most frequent order in next /coffee modal<br>Handles concurrent updates with optimistic locking | [REQ-002] | App | open |
| REQ-008 | Coffee History Query | Retrieves last 10 runs from PostgreSQL with JOIN on orders<br>Formats response with timestamp, runner, order count<br>Returns Slack message within 2 seconds<br>Handles empty history gracefully<br>Paginates if user requests more than 10 runs | [REQ-001] | App | open |
| REQ-009 | Run Cancellation Logic | Validates cancellation request from initiator or runner<br>Updates CoffeeRun status to cancelled<br>Publishes coffee.run.cancelled event to Kafka<br>Notifies all participants via Slack thread<br>Prevents cancellation after completion | [REQ-003] | App | open |
| REQ-010 | Kafka Event Consumer | Subscribes to coffee.orders, coffee.assignments, coffee.completions topics<br>Processes events idempotently with offset tracking<br>Handles deserialization errors with dead-letter queue<br>Implements circuit breaker for downstream failures<br>Logs processing metrics to Prometheus | [REQ-002, REQ-004, REQ-006] | App | open |
| REQ-011 | Audit Logging Service | Inserts AuditLog entries for all state changes<br>Captures event_type, user_id, run_id, payload as JSONB<br>Indexes by timestamp and event_type<br>Retains logs for 90 days with automated cleanup<br>Exposes audit query API for compliance | [REQ-003, REQ-006, REQ-009] | App | open |
| REQ-012 | Slack Rate Limit Resilience | Detects HTTP 429 responses from Slack API<br>Buffers events in Kafka with retry metadata<br>Implements exponential backoff (1s initial, 60s max)<br>Tracks retry attempts in Prometheus counter<br>Successfully delivers messages within 5 minutes | [REQ-005, REQ-006] | App | open |
| REQ-013 | PostgreSQL Schema Deployment | Defines tables for User, CoffeeRun, Order, UserPreference, AuditLog<br>Creates indexes on user_id, run_id, created_at<br>Configures connection pooling (max 20 connections)<br>Enables SSL for encrypted connections<br>Applies migrations via Alembic or Flyway | [] | Infra | open |
| REQ-014 | Kafka Topic Configuration | Creates topics: slack.events, coffee.orders, coffee.assignments, coffee.completions<br>Sets replication factor to 2 across 3 brokers<br>Configures partitions (3 per topic) for parallelism<br>Enables log compaction for coffee.assignments<br>Sets retention to 7 days | [] | Infra | open |
| REQ-015 | Kong Gateway Route Setup | Configures /slack/commands and /slack/interactions routes<br>Integrates OIDC plugin with Ory Hydra for token validation<br>Enforces rate limiting (100 req/min per user)<br>Adds request logging to Prometheus<br>Sets up health check endpoint /health | [] | Infra | open |
| REQ-016 | Vault Secrets Integration | Stores Slack signing secret, PostgreSQL credentials, Kafka SASL config<br>Configures Kubernetes service account for Vault access<br>Injects secrets as environment variables via init container<br>Implements secret rotation every 90 days<br>Audits secret access in Vault logs | [] | Infra | open |
| REQ-017 | Kubernetes Deployment Manifest | Defines Helm chart with 3 replicas for high availability<br>Configures resource requests (1 vCPU, 2 GB RAM per pod)<br>Sets liveness and readiness probes on /health endpoint<br>Mounts ConfigMaps for workspace_id, Kafka brokers<br>Applies PodDisruptionBudget (min 2 available) | [REQ-013, REQ-014, REQ-015, REQ-016] | Infra | open |
| REQ-018 | Observability Stack Setup | Deploys Prometheus with /metrics scrape config<br>Creates Grafana dashboards for command latency, order volume, error rates<br>Configures alerting rules for high error rate (>1%)<br>Sets up Fluentd for structured log aggregation<br>Integrates with existing on-prem monitoring | [REQ-017] | Infra | open |

### Acceptance — REQ-001
- FastAPI application starts and binds to port 8000 within 5 seconds
- POST /slack/commands endpoint returns 200 status code with valid JSON response
- Slack signature validation rejects requests with invalid signatures (returns 401)
- Command metadata (user_id, channel_id, command, timestamp) logged to stdout as structured JSON
- Supports /coffee, /coffee-history, /coffee-cancel commands with distinct handlers
- Response time measured at p95 is under 2 seconds under 50 concurrent requests
- Unit tests cover signature validation, command routing, and error handling

### Acceptance — REQ-002
- Slack modal opens within 2 seconds of /coffee command invocation
- Modal includes dropdown for drink_type (Latte, Espresso, Cappuccino, Americano, Mocha)
- Modal includes radio buttons for size (Small, Medium, Large)
- Modal includes text input for customizations (max 200 characters)
- Submitted order persisted to PostgreSQL orders table with all fields populated
- Kafka event coffee.order.placed published with order_id, user_id, drink_type, size, customizations
- User receives confirmation message in Slack thread within 5 seconds
- Integration tests verify end-to-end flow from modal submission to database persistence

### Acceptance — REQ-003
- CoffeeRun entity created with UUID primary key (run_id)
- Status field defaults to 'active' on creation
- Workspace_id and channel_id extracted from Slack payload and stored
- Initiator_user_id matches Slack user who invoked /coffee command
- Created_at timestamp set to current UTC time
- Kafka event coffee.run.created published with run_id, workspace_id, initiator_user_id
- Database transaction commits atomically (no partial writes)
- Unit tests verify entity creation with valid and invalid inputs

### Acceptance — REQ-004
- Algorithm queries CoffeeRun table for runs in last 30 days grouped by runner_user_id
- Users with zero runs in last 30 days prioritized over users with 1+ runs
- Among users with equal run counts, selection is deterministic (e.g., alphabetical by user_id)
- Users with no orders in last 14 days excluded from runner pool
- CoffeeRun.runner_user_id updated atomically using database transaction
- Kafka event coffee.runner.assigned published with run_id, runner_user_id, assignment_timestamp
- Fairness score (standard deviation of run counts) calculated and logged to Prometheus
- Integration tests verify fairness over 100 simulated runs with 10 users

### Acceptance — REQ-005
- Slack DM sent to runner within 5 minutes of assignment (measured via timestamp diff)
- DM includes formatted order summary with drink_type, size, customizations per user
- Interactive button labeled "Mark Complete" attached to DM with callback_id
- Reminder_sent_at timestamp updated in CoffeeRun table after successful DM delivery
- Exponential backoff implemented: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max) on Slack API failure
- Retry attempts logged to Prometheus counter slack_dm_retries_total
- Circuit breaker opens after 5 consecutive failures, half-opens after 30 seconds
- End-to-end test verifies DM delivery and button interaction

### Acceptance — REQ-006
- Button interaction payload validated for callback_id and runner_user_id match
- CoffeeRun status updated to 'completed' in single database transaction
- Completed_at timestamp set to current UTC time
- Kafka event coffee.run.completed published with run_id, runner_user_id, completed_at
- Completion message posted in original Slack thread within 3 seconds
- Non-runner users attempting to complete run receive error message
- Database rollback occurs if Kafka publish fails (transactional outbox pattern)
- Integration tests cover happy path and unauthorized completion attempts

### Acceptance — REQ-007
- UserPreference table stores up to 3 most recent orders per user
- Order_count incremented for each drink_type + size combination
- Last_ordered_at timestamp updated on each new order
- /coffee modal pre-fills drink_type and size from most frequent preference
- Concurrent updates handled with optimistic locking (version field or SELECT FOR UPDATE)
- Preferences older than 90 days archived or deleted
- Query performance under 100ms for preference lookup (indexed by user_id)
- Unit tests verify preference ranking and concurrent update handling

### Acceptance — REQ-008
- Query retrieves last 10 CoffeeRun records ordered by created_at DESC
- JOIN with Order table aggregates order count per run
- Response formatted as Slack message with timestamp, runner display_name, order count
- Empty history returns friendly message "No coffee runs yet!"
- Query execution time under 500ms (measured via database query log)
- Pagination supported via optional offset parameter (e.g., /coffee-history --page 2)
- Response delivered to Slack within 2 seconds of command invocation
- Integration tests verify response format and pagination logic

### Acceptance — REQ-009
- Cancellation request validated: only initiator or assigned runner can cancel
- CoffeeRun status updated to 'cancelled' in atomic transaction
- Kafka event coffee.run.cancelled published with run_id, cancelled_by_user_id, reason
- All participants (initiator + users with orders) notified via Slack thread
- Cancellation blocked if status is already 'completed' (returns error message)
- Cancelled runs excluded from runner fairness calculation
- Audit log entry created with event_type='run_cancelled'
- Unit tests cover authorization checks and state transition validation

### Acceptance — REQ-010
- Consumer subscribes to 3 topics: coffee.orders, coffee.assignments, coffee.completions
- Kafka offset committed only after successful event processing (at-least-once delivery)
- Deserialization errors (invalid JSON) routed to dead-letter queue topic
- Circuit breaker opens after 5 consecutive processing failures, half-opens after 30s
- Processing latency (event timestamp to completion) logged to Prometheus histogram
- Consumer group rebalancing handled gracefully (no message loss)
- Idempotency ensured via event_id deduplication in PostgreSQL
- Integration tests verify end-to-end event flow with simulated failures

### Acceptance — REQ-011
- AuditLog table insert occurs within same transaction as state change
- Event_type values: order_placed, runner_assigned, run_completed, run_cancelled
- Payload field stores full event context as JSONB (queryable)
- Composite index on (timestamp, event_type) for fast range queries
- Automated cleanup job deletes logs older than 90 days (runs daily at 2am)
- Audit query API endpoint GET /api/v1/audit?start_date=X&end_date=Y returns paginated results
- Query performance under 1 second for 90-day range with 10k events
- Compliance tests verify log retention and query accuracy

### Acceptance — REQ-012
- HTTP 429 response from Slack API detected and logged to Prometheus counter
- Event buffered in Kafka topic slack.retry with retry_count metadata
- Exponential backoff schedule: 1s, 2s, 4s, 8s, 16s, 32s, 60s (capped at 60s)
- Retry consumer processes slack.retry topic with delay based on retry_count
- Successful delivery after retry removes event from retry queue
- Max retry attempts set to 10; after 10 failures, event moved to dead-letter queue
- End-to-end latency (initial attempt to successful delivery) under 5 minutes for 95% of retries
- Load tests verify resilience under sustained rate limiting (50 req/min)

### Acceptance — REQ-013
- Alembic migration scripts create 5 tables: users, coffee_runs, orders, user_preferences, audit_logs
- Indexes created: users(user_id), coffee_runs(run_id, status, created_at), orders(run_id, user_id)
- Connection pool configured with max_connections=20, overflow=5, pool_timeout=30s
- SSL mode set to 'require' with certificate validation
- Migration rollback tested for last 3 versions
- Database health check query (SELECT 1) returns within 100ms
- Schema documentation generated and stored in docs/schema.md
- CI pipeline runs migrations against test database before deployment

### Acceptance — REQ-014
- 4 Kafka topics created: slack.events, coffee.orders, coffee.assignments, coffee.completions
- Replication factor set to 2 (tolerates 1 broker failure)
- Partition count set to 3 per topic (supports 3 concurrent consumers)
- Log compaction enabled for coffee.assignments (retains latest assignment per run_id)
- Retention period set to 7 days (168 hours)
- Topic creation idempotent (script can run multiple times without errors)
- Kafka health check verifies all topics exist and are writable
- Documentation includes topic schemas and partition key strategies

### Acceptance — REQ-015
- Kong routes /slack/commands and /slack/interactions to CoffeeBuddy service
- OIDC plugin configured with Ory Hydra issuer URL and client credentials
- Rate limiting plugin enforces 100 req/min per consumer (identified by user_id claim)
- Request logging plugin sends metrics to Prometheus (status code, latency, path)
- Health check route /health bypasses authentication and returns 200 with uptime
- Invalid OIDC tokens return 401 with WWW-Authenticate header
- Kong admin API accessible only from internal network (firewall rule)
- Load tests verify rate limiting accuracy under 200 req/min load

### Acceptance — REQ-016
- Vault KV secrets engine stores slack_signing_secret, postgres_password, kafka_sasl_password
- Kubernetes service account coffeebuddy-sa granted read access to secrets path
- Init container fetches secrets and writes to /vault/secrets/ volume
- Application reads secrets from environment variables (injected from volume)
- Secret rotation script updates Vault and triggers pod restart (zero downtime)
- Vault audit log records all secret access with timestamp and service account
- Secrets never logged to stdout or stored in ConfigMaps
- Security scan verifies no hardcoded secrets in container image

### Acceptance — REQ-017
- Helm chart deploys 3 replicas of CoffeeBuddy service across 3 nodes
- Resource requests: 1 vCPU, 2 GB RAM per pod; limits: 2 vCPU, 4 GB RAM
- Liveness probe: HTTP GET /health every 10s, failure threshold 3
- Readiness probe: HTTP GET /health every 5s, success threshold 1
- ConfigMap mounts workspace_id, kafka_brokers, postgres_host as environment variables
- PodDisruptionBudget ensures minimum 2 pods available during rolling updates
- Rolling update strategy: maxUnavailable=1, maxSurge=1
- Helm upgrade tested with zero downtime (verified via continuous load test)

### Acceptance — REQ-018
- Prometheus scrapes /metrics endpoint every 15 seconds from all pods
- Grafana dashboard includes panels: command latency (p50, p95, p99), order volume (rate), error rate (%)
- Alerting rule fires if error rate exceeds 1% over 5-minute window
- Fluentd DaemonSet collects logs from all pods and forwards to internal Elasticsearch
- Log retention set to 30 days in Elasticsearch
- Dashboard accessible at https://grafana.internal/d/coffeebuddy
- Alert notification sent to Slack channel #ops-alerts
- Runbook linked in alert annotation with troubleshooting steps

## Dependency Graph (textual)

```
REQ-001 -> (no dependencies)
REQ-002 -> REQ-001
REQ-003 -> REQ-001
REQ-004 -> REQ-003
REQ-005 -> REQ-004
REQ-006 -> REQ-005
REQ-007 -> REQ-002
REQ-008 -> REQ-001
REQ-009 -> REQ-003
REQ-010 -> REQ-002, REQ-004, REQ-006
REQ-011 -> REQ-003, REQ-006, REQ-009
REQ-012 -> REQ-005, REQ-006
REQ-013 -> (no dependencies)
REQ-014 -> (no dependencies)
REQ-015 -> (no dependencies)
REQ-016 -> (no dependencies)
REQ-017 -> REQ-013, REQ-014, REQ-015, REQ-016
REQ-018 -> REQ-017
```

**Critical Path:** REQ-001 → REQ-003 → REQ-004 → REQ-005 → REQ-006 (App Track)

**Parallel Tracks:**
- App Track: REQ-001 through REQ-012 (can proceed independently)
- Infra Track: REQ-013 through REQ-016 (can proceed in parallel with App)
- Integration: REQ-017 and REQ-018 (require both tracks complete)

## Iteration Strategy

**Batch 1 (Foundation):** REQ-001, REQ-013, REQ-014, REQ-015, REQ-016
- **Size:** Medium (2-3 days)
- **Goal:** Establish API foundation, database schema, Kafka topics, Kong routes, Vault secrets
- **Confidence:** High (±0 batches) — well-defined infrastructure setup

**Batch 2 (Core Workflows):** REQ-002, REQ-003, REQ-004
- **Size:** Medium (2-3 days)
- **Goal:** Implement order submission, run lifecycle, runner assignment algorithm
- **Confidence:** High (±0 batches) — core business logic with clear acceptance criteria

**Batch 3 (Notifications & Completion):** REQ-005, REQ-006, REQ-012
- **Size:** Medium (2-3 days)
- **Goal:** Runner notifications, run completion, Slack rate limit resilience
- **Confidence:** Medium (±1 batch) — depends on Slack API behavior and retry logic complexity

**Batch 4 (User Features):** REQ-007, REQ-008, REQ-009
- **Size:** Small (1-2 days)
- **Goal:** User preferences, history query, run cancellation
- **Confidence:** High (±0 batches) — straightforward CRUD operations

**Batch 5 (Event Processing & Audit):** REQ-010, REQ-011
- **Size:** Medium (2-3 days)
- **Goal:** Kafka event consumer, audit logging service
- **Confidence:** Medium (±1 batch) — requires careful idempotency and error handling

**Batch 6 (Deployment & Observability):** REQ-017, REQ-018
- **Size:** Small (1-2 days)
- **Goal:** Kubernetes deployment, Prometheus/Grafana setup
- **Confidence:** High (±0 batches) — standard deployment patterns

**Total Estimated Duration:** 12-18 days (assuming 1 developer, sequential batches)

## Test Strategy

**Per-REQ Testing:**
- **Unit Tests:** All business logic functions (runner assignment, fairness calculation, preference ranking) with 80%+ code coverage
- **Integration Tests:** API endpoints with mocked Slack API, PostgreSQL test database, embedded Kafka (Testcontainers)
- **Contract Tests:** Kafka event schemas validated against JSON Schema definitions
- **Security Tests:** OIDC token validation, Slack signature verification, SQL injection prevention

**Per-Batch Testing:**
- **Batch 1:** Infrastructure smoke tests (database connectivity, Kafka topic creation, Kong route health)
- **Batch 2:** End-to-end workflow tests (order submission → runner assignment)
- **Batch 3:** Resilience tests (Slack API rate limiting simulation, retry logic verification)
- **Batch 4:** User experience tests (preference suggestion accuracy, history pagination)
- **Batch 5:** Event processing tests (idempotency, dead-letter queue handling)
- **Batch 6:** Deployment tests (rolling update zero downtime, health check validation)

**End-to-End Testing:**
- **Scenario 1:** 10 users submit orders within 5 minutes → runner assigned → completion within 10 minutes
- **Scenario 2:** Slack API returns 429 → events buffered → successful delivery within 5 minutes
- **Scenario 3:** Database connection fails → circuit breaker opens → recovery after 30 seconds
- **Scenario 4:** 100 concurrent /coffee commands → all respond within 2 seconds → no errors

**Performance Testing:**
- **Load Test:** 50 concurrent users, 100 orders/day sustained for 1 hour
- **Stress Test:** 200 concurrent users, 500 orders/day for 10 minutes (identify breaking point)
- **Soak Test:** 10 concurrent users, 50 orders/day for 24 hours (detect memory leaks)

## KIT Readiness (per REQ)

**REQ-001 (Slack Command Handler Foundation):**
- **Paths:** `/runs/kit/REQ-001/src/handlers/slack_commands.py`, `/runs/kit/REQ-001/test/test_slack_commands.py`
- **Scaffolds:** FastAPI app with /slack/commands endpoint, signature validation middleware, command router
- **Commands:** `pytest test/test_slack_commands.py`, `uvicorn src.main:app --reload`
- **Expected:** All tests pass, endpoint returns 200 with valid JSON, signature validation rejects invalid requests
- **KIT-functional:** Yes

**REQ-002 (Order Submission Modal):**
- **Paths:** `/runs/kit/REQ-002/src/handlers/order_modal.py`, `/runs/kit/REQ-002/test/test_order_modal.py`
- **Scaffolds:** Modal view definition, submission handler, PostgreSQL insert, Kafka producer
- **Commands:** `pytest test/test_order_modal.py --cov=src`, `docker-compose up postgres kafka`
- **Expected:** Modal opens, order persisted, Kafka event published, confirmation message sent
- **KIT-functional:** Yes

**REQ-003 (Coffee Run Lifecycle Management):**
- **Paths:** `/runs/kit/REQ-003/src/models/coffee_run.py`, `/runs/kit/REQ-003/test/test_coffee_run.py`
- **Scaffolds:** CoffeeRun SQLAlchemy model, create_run service function, Kafka event publisher
- **Commands:** `pytest test/test_coffee_run.py`, `alembic upgrade head`
- **Expected:** Run created with UUID, status=active, Kafka event published
- **KIT-functional:** Yes

**REQ-004 (Runner Assignment Algorithm):**
- **Paths:** `/runs/kit/REQ-004/src/services/runner_assignment.py`, `/runs/kit/REQ-004/test/test_runner_assignment.py`
- **Scaffolds:** Fairness calculation function, database query, atomic update, Kafka publisher
- **Commands:** `pytest test/test_runner_assignment.py --cov=src.services`, `python -m src.services.runner_assignment`
- **Expected:** Runner selected based on fairness, CoffeeRun updated, event published
- **KIT-functional:** Yes

**REQ-005 (Runner Notification System):**
- **Paths:** `/runs/kit/REQ-005/src/services/notifications.py`, `/runs/kit/REQ-005/test/test_notifications.py`
- **Scaffolds:** Slack DM sender with retry logic, exponential backoff, circuit breaker
- **Commands:** `pytest test/test_notifications.py`, `python -m src.services.notifications --dry-run`
- **Expected:** DM sent within 5 minutes, retry on failure, circuit breaker opens after 5 failures
- **KIT-functional:** Yes

**REQ-006 (Run Completion Handler):**
- **Paths:** `/runs/kit/REQ-006/src/handlers/completion.py`, `/runs/kit/REQ-006/test/test_completion.py`
- **Scaffolds:** Button interaction handler, status update, Kafka publisher, thread message poster
- **Commands:** `pytest test/test_completion.py`, `curl -X POST http://localhost:8000/slack/interactions`
- **Expected:** Status updated to completed, event published, message posted in thread
- **KIT-functional:** Yes

**REQ-007 (User Preference Tracking):**
- **Paths:** `/runs/kit/REQ-007/src/services/preferences.py`, `/runs/kit/REQ-007/test/test_preferences.py`
- **Scaffolds:** UserPreference model, upsert logic, optimistic locking, preference ranking
- **Commands:** `pytest test/test_preferences.py --cov=src.services`, `python -m src.services.preferences`
- **Expected:** Preferences stored, order_count incremented, last_ordered_at updated
- **KIT-functional:** Yes

**REQ-008 (Coffee History Query):**
- **Paths:** `/runs/kit/REQ-008/src/handlers/history.py`, `/runs/kit/REQ-008/test/test_history.py`
- **Scaffolds:** History query function, JOIN with orders, Slack message formatter
- **Commands:** `pytest test/test_history.py`, `curl http://localhost:8000/api/v1/history?user_id=U123`
- **Expected:** Last 10 runs retrieved, formatted message returned within 2 seconds
- **KIT-functional:** Yes

**REQ-009 (Run Cancellation Logic):**
- **Paths:** `/runs/kit/REQ-009/src/handlers/cancellation.py`, `/runs/kit/REQ-009/test/test_cancellation.py`
- **Scaffolds:** Authorization check, status update, Kafka publisher, participant notification
- **Commands:** `pytest test/test_cancellation.py`, `curl -X POST http://localhost:8000/api/v1/runs/{run_id}/cancel`
- **Expected:** Run cancelled, event published, participants notified, completed runs rejected
- **KIT-functional:** Yes

**REQ-010 (Kafka Event Consumer):**
- **Paths:** `/runs/kit/REQ-010/src/consumers/event_consumer.py`, `/runs/kit/REQ-010/test/test_event_consumer.py`
- **Scaffolds:** Kafka consumer with offset management, circuit breaker, dead-letter queue
- **Commands:** `pytest test/test_event_consumer.py`, `python -m src.consumers.event_consumer`
- **Expected:** Events consumed, processed idempotently, failures routed to DLQ
- **KIT-functional:** Yes

**REQ-011 (Audit Logging Service):**
- **Paths:** `/runs/kit/REQ-011/src/services/audit.py`, `/runs/kit/REQ-011/test/test_audit.py`
- **Scaffolds:** AuditLog model, insert function, cleanup job, query API
- **Commands:** `pytest test/test_audit.py`, `python -m src.services.audit --cleanup`
- **Expected:** Logs inserted, retained for 90 days, query API returns paginated results
- **KIT-functional:** Yes

**REQ-012 (Slack Rate Limit Resilience):**
- **Paths:** `/runs/kit/REQ-012/src/services/retry.py`, `/runs/kit/REQ-012/test/test_retry.py`
- **Scaffolds:** Retry consumer, exponential backoff scheduler, DLQ handler
- **Commands:** `pytest test/test_retry.py`, `python -m src.services.retry`
- **Expected:** 429 detected, event buffered, retried with backoff, delivered within 5 minutes
- **KIT-functional:** Yes

**REQ-013 (PostgreSQL Schema Deployment):**
- **Paths:** `/runs/kit/REQ-013/migrations/`, `/runs/kit/REQ-013/test/test_migrations.py`
- **Scaffolds:** Alembic migration scripts, rollback tests, connection pool config
- **Commands:** `alembic upgrade head`, `alembic downgrade -1`, `pytest test/test_migrations.py`
- **Expected:** Tables created, indexes applied, SSL enabled, migrations reversible
- **KIT-functional:** Yes

**REQ-014 (Kafka Topic Configuration):**
- **Paths:** `/runs/kit/REQ-014/scripts/create_topics.sh`, `/runs/kit/REQ-014/test/test_topics.py`
- **Scaffolds:** Kafka Admin API script, topic config YAML, health check
- **Commands:** `./scripts/create_topics.sh`, `pytest test/test_topics.py`
- **Expected:** 4 topics created, replication factor 2, partitions 3
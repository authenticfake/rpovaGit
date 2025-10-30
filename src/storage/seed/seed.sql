-- CoffeeBuddy Seed Data
-- Description: Idempotent seed data for development and testing
-- Author: Harper /kit
-- Date: 2025-01-20

-- Insert test users (idempotent via ON CONFLICT)
INSERT INTO users (user_id, display_name, email, created_at, updated_at)
VALUES
    ('U001', 'Alice Johnson', 'alice.johnson@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U002', 'Bob Smith', 'bob.smith@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U003', 'Charlie Davis', 'charlie.davis@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U004', 'Diana Prince', 'diana.prince@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U005', 'Eve Martinez', 'eve.martinez@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U006', 'Frank Wilson', 'frank.wilson@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U007', 'Grace Lee', 'grace.lee@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U008', 'Henry Brown', 'henry.brown@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U009', 'Ivy Chen', 'ivy.chen@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U010', 'Jack Taylor', 'jack.taylor@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U011', 'Karen White', 'karen.white@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U012', 'Leo Garcia', 'leo.garcia@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U013', 'Mia Anderson', 'mia.anderson@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U014', 'Noah Thomas', 'noah.thomas@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('U015', 'Olivia Moore', 'olivia.moore@company.com', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (user_id) DO NOTHING;

-- Insert test coffee runs (idempotent via ON CONFLICT)
INSERT INTO coffee_runs (run_id, workspace_id, channel_id, initiator_user_id, runner_user_id, status, created_at, completed_at, reminder_sent_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'WS001', 'CH001', 'U001', 'U002', 'completed', CURRENT_TIMESTAMP - INTERVAL '7 days', CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '30 minutes', CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '5 minutes'),
    ('22222222-2222-2222-2222-222222222222', 'WS001', 'CH001', 'U003', 'U004', 'completed', CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '25 minutes', CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '5 minutes'),
    ('33333333-3333-3333-3333-333333333333', 'WS001', 'CH001', 'U005', 'U006', 'completed', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days' + INTERVAL '20 minutes', CURRENT_TIMESTAMP - INTERVAL '3 days' + INTERVAL '5 minutes'),
    ('44444444-4444-4444-4444-444444444444', 'WS001', 'CH001', 'U007', 'U008', 'active', CURRENT_TIMESTAMP - INTERVAL '1 hour', NULL, CURRENT_TIMESTAMP - INTERVAL '55 minutes'),
    ('55555555-5555-5555-5555-555555555555', 'WS001', 'CH002', 'U009', NULL, 'active', CURRENT_TIMESTAMP - INTERVAL '10 minutes', NULL, NULL)
ON CONFLICT (run_id) DO NOTHING;

-- Insert test orders (idempotent via ON CONFLICT)
INSERT INTO orders (order_id, run_id, user_id, drink_type, size, customizations, created_at)
VALUES
    ('a1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'U001', 'Latte', 'Medium', '["Extra shot", "Oat milk"]', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('a2222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'U003', 'Espresso', 'Small', '[]', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('a3333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'U005', 'Cappuccino', 'Large', '["Extra foam"]', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('b1111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'U003', 'Americano', 'Medium', '[]', CURRENT_TIMESTAMP - INTERVAL '5 days'),
    ('b2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'U007', 'Mocha', 'Large', '["Whipped cream"]', CURRENT_TIMESTAMP - INTERVAL '5 days'),
    ('c1111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', 'U005', 'Latte', 'Medium', '["Almond milk"]', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    ('c2222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', 'U009', 'Flat White', 'Small', '[]', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    ('c3333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333', 'U011', 'Cortado', 'Small', '[]', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    ('d1111111-1111-1111-1111-111111111111', '44444444-4444-4444-4444-444444444444', 'U007', 'Latte', 'Large', '["Extra shot", "Soy milk"]', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
    ('d2222222-2222-2222-2222-222222222222', '44444444-4444-4444-4444-444444444444', 'U013', 'Cappuccino', 'Medium', '[]', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
    ('e1111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-555555555555', 'U009', 'Espresso', 'Small', '[]', CURRENT_TIMESTAMP - INTERVAL '10 minutes')
ON CONFLICT (order_id) DO NOTHING;

-- Insert test user preferences (idempotent via ON CONFLICT)
INSERT INTO user_preferences (preference_id, user_id, drink_type, size, customizations, order_count, last_ordered_at)
VALUES
    ('p1111111-1111-1111-1111-111111111111', 'U001', 'Latte', 'Medium', '["Extra shot", "Oat milk"]', 3, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('p2222222-2222-2222-2222-222222222222', 'U003', 'Espresso', 'Small', '[]', 2, CURRENT_TIMESTAMP - INTERVAL '5 days'),
    ('p3333333-3333-3333-3333-333333333333', 'U005', 'Latte', 'Medium', '["Almond milk"]', 4, CURRENT_TIMESTAMP - INTERVAL '3 days'),
    ('p4444444-4444-4444-4444-444444444444', 'U007', 'Latte', 'Large', '["Extra shot", "Soy milk"]', 2, CURRENT_TIMESTAMP - INTERVAL '1 hour'),
    ('p5555555-5555-5555-5555-555555555555', 'U009', 'Espresso', 'Small', '[]', 3, CURRENT_TIMESTAMP - INTERVAL '10 minutes')
ON CONFLICT (preference_id) DO NOTHING;

-- Insert test audit logs (idempotent via ON CONFLICT)
INSERT INTO audit_logs (log_id, event_type, user_id, run_id, payload, timestamp)
VALUES
    ('l1111111-1111-1111-1111-111111111111', 'run_created', 'U001', '11111111-1111-1111-1111-111111111111', '{"workspace_id": "WS001", "channel_id": "CH001"}', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('l2222222-2222-2222-2222-222222222222', 'order_placed', 'U001', '11111111-1111-1111-1111-111111111111', '{"drink_type": "Latte", "size": "Medium"}', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('l3333333-3333-3333-3333-333333333333', 'runner_assigned', 'U002', '11111111-1111-1111-1111-111111111111', '{"runner_user_id": "U002"}', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('l4444444-4444-4444-4444-444444444444', 'run_completed', 'U002', '11111111-1111-1111-1111-111111111111', '{"completed_at": "2025-01-13T10:30:00Z"}', CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '30 minutes'),
    ('l5555555-5555-5555-5555-555555555555', 'run_created', 'U003', '22222222-2222-2222-2222-222222222222', '{"workspace_id": "WS001", "channel_id": "CH001"}', CURRENT_TIMESTAMP - INTERVAL '5 days')
ON CONFLICT (log_id) DO NOTHING;
```

```python
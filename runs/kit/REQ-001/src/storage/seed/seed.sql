-- seed.sql: Idempotent seed data for development/testing
-- Safe to run multiple times

-- Insert test users (idempotent via ON CONFLICT)
INSERT INTO users (user_id, display_name, email, created_at, updated_at)
VALUES
    ('U001', 'Alice Johnson', 'alice.johnson@company.com', NOW(), NOW()),
    ('U002', 'Bob Smith', 'bob.smith@company.com', NOW(), NOW()),
    ('U003', 'Carol White', 'carol.white@company.com', NOW(), NOW()),
    ('U004', 'David Brown', 'david.brown@company.com', NOW(), NOW()),
    ('U005', 'Eve Davis', 'eve.davis@company.com', NOW(), NOW()),
    ('U006', 'Frank Miller', 'frank.miller@company.com', NOW(), NOW()),
    ('U007', 'Grace Wilson', 'grace.wilson@company.com', NOW(), NOW()),
    ('U008', 'Henry Moore', 'henry.moore@company.com', NOW(), NOW()),
    ('U009', 'Ivy Taylor', 'ivy.taylor@company.com', NOW(), NOW()),
    ('U010', 'Jack Anderson', 'jack.anderson@company.com', NOW(), NOW())
ON CONFLICT (user_id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    email = EXCLUDED.email,
    updated_at = NOW();

-- Insert historical coffee runs (idempotent via explicit IDs and ON CONFLICT)
INSERT INTO coffee_runs (run_id, workspace_id, channel_id, initiator_user_id, runner_user_id, status, created_at, completed_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'WS001', 'C001', 'U001', 'U002', 'completed', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days' + INTERVAL '1 hour'),
    ('22222222-2222-2222-2222-222222222222', 'WS001', 'C001', 'U003', 'U004', 'completed', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days' + INTERVAL '1 hour'),
    ('33333333-3333-3333-3333-333333333333', 'WS001', 'C001', 'U005', 'U006', 'completed', NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days' + INTERVAL '1 hour'),
    ('44444444-4444-4444-4444-444444444444', 'WS001', 'C001', 'U007', 'U008', 'completed', NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days' + INTERVAL '1 hour'),
    ('55555555-5555-5555-5555-555555555555', 'WS001', 'C001', 'U009', 'U010', 'completed', NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days' + INTERVAL '1 hour'),
    ('66666666-6666-6666-6666-666666666666', 'WS001', 'C001', 'U001', 'U003', 'completed', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days' + INTERVAL '1 hour'),
    ('77777777-7777-7777-7777-777777777777', 'WS001', 'C001', 'U002', 'U005', 'completed', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '1 hour'),
    ('88888888-8888-8888-8888-888888888888', 'WS001', 'C001', 'U004', 'U007', 'completed', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '1 hour'),
    ('99999999-9999-9999-9999-999999999999', 'WS001', 'C001', 'U006', 'U009', 'completed', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '1 hour'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'WS001', 'C001', 'U008', 'U001', 'active', NOW() - INTERVAL '1 hour', NULL)
ON CONFLICT (run_id) DO NOTHING;

-- Insert orders for historical runs
INSERT INTO orders (order_id, run_id, user_id, drink_type, size, customizations, created_at)
VALUES
    ('o1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'U001', 'Latte', 'Medium', '["Extra shot", "Oat milk"]', NOW() - INTERVAL '30 days'),
    ('o2222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'U003', 'Cappuccino', 'Small', '[]', NOW() - INTERVAL '30 days'),
    ('o3333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'U003', 'Espresso', 'Small', '["Double shot"]', NOW() - INTERVAL '25 days'),
    ('o4444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', 'U005', 'Americano', 'Large', '[]', NOW() - INTERVAL '25 days'),
    ('o5555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333', 'U005', 'Mocha', 'Medium', '["Whipped cream"]', NOW() - INTERVAL '20 days'),
    ('o6666666-6666-6666-6666-666666666666', '33333333-3333-3333-3333-333333333333', 'U007', 'Latte', 'Large', '["Vanilla syrup"]', NOW() - INTERVAL '20 days'),
    ('o7777777-7777-7777-7777-777777777777', '44444444-4444-4444-4444-444444444444', 'U007', 'Flat White', 'Small', '[]', NOW() - INTERVAL '15 days'),
    ('o8888888-8888-8888-8888-888888888888', '44444444-4444-4444-4444-444444444444', 'U009', 'Cappuccino', 'Medium', '["Extra foam"]', NOW() - INTERVAL '15 days'),
    ('o9999999-9999-9999-9999-999999999999', '55555555-5555-5555-5555-555555555555', 'U009', 'Latte', 'Medium', '["Almond milk"]', NOW() - INTERVAL '10 days'),
    ('oaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 'U001', 'Espresso', 'Small', '[]', NOW() - INTERVAL '10 days')
ON CONFLICT (order_id) DO NOTHING;

-- Insert user preferences based on orders
INSERT INTO user_preferences (preference_id, user_id, drink_type, size, customizations, order_count, last_ordered_at)
VALUES
    ('p1111111-1111-1111-1111-111111111111', 'U001', 'Latte', 'Medium', '["Extra shot", "Oat milk"]', 2, NOW() - INTERVAL '10 days'),
    ('p2222222-2222-2222-2222-222222222222', 'U003', 'Cappuccino', 'Small', '[]', 1, NOW() - INTERVAL '30 days'),
    ('p3333333-3333-3333-3333-333333333333', 'U003', 'Espresso', 'Small', '["Double shot"]', 1, NOW() - INTERVAL '25 days'),
    ('p4444444-4444-4444-4444-444444444444', 'U005', 'Americano', 'Large', '[]', 1, NOW() - INTERVAL '25 days'),
    ('p5555555-5555-5555-5555-555555555555', 'U005', 'Mocha', 'Medium', '["Whipped cream"]', 1, NOW() - INTERVAL '20 days'),
    ('p6666666-6666-6666-6666-666666666666', 'U007', 'Latte', 'Large', '["Vanilla syrup"]', 1, NOW() - INTERVAL '20 days'),
    ('p7777777-7777-7777-7777-777777777777', 'U007', 'Flat White', 'Small', '[]', 1, NOW() - INTERVAL '15 days'),
    ('p8888888-8888-8888-8888-888888888888', 'U009', 'Cappuccino', 'Medium', '["Extra foam"]', 1, NOW() - INTERVAL '15 days'),
    ('p9999999-9999-9999-9999-999999999999', 'U009', 'Latte', 'Medium', '["Almond milk"]', 1, NOW() - INTERVAL '10 days'),
    ('paaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'U001', 'Espresso', 'Small', '[]', 1, NOW() - INTERVAL '10 days')
ON CONFLICT ON CONSTRAINT idx_user_preferences_unique DO UPDATE SET
    order_count = user_preferences.order_count + 1,
    last_ordered_at = EXCLUDED.last_ordered_at;

-- Insert audit log entries
INSERT INTO audit_logs (log_id, event_type, user_id, run_id, payload, timestamp)
VALUES
    ('a1111111-1111-1111-1111-111111111111', 'run_created', 'U001', '11111111-1111-1111-1111-111111111111', '{"workspace_id": "WS001", "channel_id": "C001"}', NOW() - INTERVAL '30 days'),
    ('a2222222-2222-2222-2222-222222222222', 'order_placed', 'U001', '11111111-1111-1111-1111-111111111111', '{"drink_type": "Latte", "size": "Medium"}', NOW() - INTERVAL '30 days'),
    ('a3333333-3333-3333-3333-333333333333', 'runner_assigned', 'U002', '11111111-1111-1111-1111-111111111111', '{"runner_user_id": "U002"}', NOW() - INTERVAL '30 days'),
    ('a4444444-4444-4444-4444-444444444444', 'run_completed', 'U002', '11111111-1111-1111-1111-111111111111', '{"completed_at": "' || (NOW() - INTERVAL '30 days' + INTERVAL '1 hour')::text || '"}', NOW() - INTERVAL '30 days' + INTERVAL '1 hour'),
    ('a5555555-5555-5555-5555-555555555555', 'run_created', 'U003', '22222222-2222-2222-2222-222222222222', '{"workspace_id": "WS001", "channel_id": "C001"}', NOW() - INTERVAL '25 days'),
    ('a6666666-6666-6666-6666-666666666666', 'order_placed', 'U003', '22222222-2222-2222-2222-222222222222', '{"drink_type": "Espresso", "size": "Small"}', NOW() - INTERVAL '25 days'),
    ('a7777777-7777-7777-7777-777777777777', 'runner_assigned', 'U004', '22222222-2222-2222-2222-222222222222', '{"runner_user_id": "U004"}', NOW() - INTERVAL '25 days'),
    ('a8888888-8888-8888-8888-888888888888', 'run_completed', 'U004', '22222222-2222-2222-2222-222222222222', '{"completed_at": "' || (NOW() - INTERVAL '25 days' + INTERVAL '1 hour')::text || '"}', NOW() - INTERVAL '25 days' + INTERVAL '1 hour'),
    ('a9999999-9999-9999-9999-999999999999', 'run_created', 'U008', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '{"workspace_id": "WS001", "channel_id": "C001"}', NOW() - INTERVAL '1 hour'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'runner_assigned', 'U001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '{"runner_user_id": "U001"}', NOW() - INTERVAL '1 hour')
ON CONFLICT (log_id) DO NOTHING;
```

```bash
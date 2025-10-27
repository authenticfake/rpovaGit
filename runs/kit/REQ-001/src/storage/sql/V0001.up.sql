-- V0001.up.sql: Initial schema for CoffeeBuddy
-- Idempotent: Safe to run multiple times

-- Create ENUM types
DO $$ BEGIN
    CREATE TYPE run_status AS ENUM ('active', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);

-- Coffee runs table
CREATE TABLE IF NOT EXISTS coffee_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR(64) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    initiator_user_id VARCHAR(64) NOT NULL,
    runner_user_id VARCHAR(64),
    status run_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    reminder_sent_at TIMESTAMP,
    CONSTRAINT fk_initiator FOREIGN KEY (initiator_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_runner FOREIGN KEY (runner_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_coffee_runs_workspace ON coffee_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_channel ON coffee_runs(channel_id);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_status ON coffee_runs(status);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_created_at ON coffee_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_runner ON coffee_runs(runner_user_id);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    drink_type VARCHAR(100) NOT NULL,
    size VARCHAR(20) NOT NULL,
    customizations TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_order_run FOREIGN KEY (run_id) REFERENCES coffee_runs(run_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_orders_run ON orders(run_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    drink_type VARCHAR(100) NOT NULL,
    size VARCHAR(20) NOT NULL,
    customizations TEXT,
    order_count INT NOT NULL DEFAULT 1,
    last_ordered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_preference_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_last_ordered ON user_preferences(last_ordered_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_preferences_unique ON user_preferences(user_id, drink_type, size, COALESCE(customizations, ''));

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(64),
    run_id UUID,
    payload JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_run FOREIGN KEY (run_id) REFERENCES coffee_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_run ON audit_logs(run_id);

-- Trigger for updated_at on users
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ BEGIN
    CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Function to prune old audit logs (90 days retention)
CREATE OR REPLACE FUNCTION prune_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Function to prune old preferences (90 days retention)
CREATE OR REPLACE FUNCTION prune_old_preferences()
RETURNS void AS $$
BEGIN
    DELETE FROM user_preferences WHERE last_ordered_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
```

```sql
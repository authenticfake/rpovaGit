-- CoffeeBuddy Database Schema V0001
-- Description: Initial schema with User, CoffeeRun, Order, UserPreference, AuditLog entities
-- Author: Harper /kit
-- Date: 2025-01-20

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);

-- CoffeeRun table
CREATE TABLE IF NOT EXISTS coffee_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id VARCHAR(64) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    initiator_user_id VARCHAR(64) NOT NULL,
    runner_user_id VARCHAR(64),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    reminder_sent_at TIMESTAMP,
    CONSTRAINT fk_initiator FOREIGN KEY (initiator_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_runner FOREIGN KEY (runner_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_coffee_runs_workspace_id ON coffee_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_channel_id ON coffee_runs(channel_id);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_status ON coffee_runs(status);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_created_at ON coffee_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_initiator_user_id ON coffee_runs(initiator_user_id);
CREATE INDEX IF NOT EXISTS idx_coffee_runs_runner_user_id ON coffee_runs(runner_user_id);

-- Order table
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    drink_type VARCHAR(100) NOT NULL,
    size VARCHAR(20) NOT NULL,
    customizations TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_run FOREIGN KEY (run_id) REFERENCES coffee_runs(run_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_orders_run_id ON orders(run_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- UserPreference table
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL,
    drink_type VARCHAR(100) NOT NULL,
    size VARCHAR(20) NOT NULL,
    customizations TEXT,
    order_count INT NOT NULL DEFAULT 1,
    last_ordered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_preference_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_last_ordered_at ON user_preferences(last_ordered_at);

-- AuditLog table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(64),
    run_id UUID,
    payload JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_run FOREIGN KEY (run_id) REFERENCES coffee_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_run_id ON audit_logs(run_id);

-- Trigger to update users.updated_at on modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to prune old audit logs (90 days retention)
CREATE OR REPLACE FUNCTION prune_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_logs WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Function to prune old user preferences (90 days retention)
CREATE OR REPLACE FUNCTION prune_old_user_preferences()
RETURNS void AS $$
BEGIN
    DELETE FROM user_preferences WHERE last_ordered_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
```

```sql
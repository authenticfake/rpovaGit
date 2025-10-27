-- V0001.down.sql: Rollback initial schema
-- Idempotent: Safe to run multiple times

-- Drop triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS prune_old_audit_logs();
DROP FUNCTION IF EXISTS prune_old_preferences();

-- Drop tables (order matters due to foreign keys)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS coffee_runs;
DROP TABLE IF EXISTS users;

-- Drop types
DROP TYPE IF EXISTS run_status;
```

```sql
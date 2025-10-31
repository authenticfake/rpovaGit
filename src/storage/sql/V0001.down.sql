-- CoffeeBuddy Database Schema V0001 Rollback
-- Description: Drop all tables and functions in reverse dependency order
-- Author: Harper /kit
-- Date: 2025-01-20

-- Drop triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS prune_old_audit_logs();
DROP FUNCTION IF EXISTS prune_old_user_preferences();

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS coffee_runs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop extension
DROP EXTENSION IF EXISTS "uuid-ossp";
```

```sql
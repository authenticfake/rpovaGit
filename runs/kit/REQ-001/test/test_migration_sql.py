"""
test_migration_sql.py: Shape tests for database schema
Tests idempotency, round-trip, and schema validation
"""
import os
import subprocess
import pytest
from typing import Generator
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


@pytest.fixture(scope="module")
def database_url() -> str:
    """Get database URL from environment or skip tests."""
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; skipping database tests")
    return url


@pytest.fixture(scope="module")
def db_connection(database_url: str) -> Generator:
    """Create test database connection."""
    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    yield conn
    conn.close()


def run_script(script_name: str, database_url: str) -> None:
    """Execute a shell script with DATABASE_URL."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", script_name
    )
    result = subprocess.run(
        [script_path, database_url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Script {script_name} failed:\n{result.stdout}\n{result.stderr}"
        )


def test_migration_up_creates_tables(db_connection, database_url: str) -> None:
    """Test that upgrade migration creates all expected tables."""
    # Clean slate
    run_script("db_downgrade.sh", database_url)
    
    # Apply migrations
    run_script("db_upgrade.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        "audit_logs",
        "coffee_runs",
        "orders",
        "user_preferences",
        "users",
    ]
    
    assert set(expected_tables).issubset(set(tables)), (
        f"Missing tables. Expected: {expected_tables}, Got: {tables}"
    )


def test_migration_idempotency(db_connection, database_url: str) -> None:
    """Test that running migrations multiple times is safe."""
    # Apply migrations twice
    run_script("db_upgrade.sh", database_url)
    run_script("db_upgrade.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    count_after_first = cursor.fetchone()[0]
    
    run_script("db_upgrade.sh", database_url)
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    count_after_second = cursor.fetchone()[0]
    
    assert count_after_first == count_after_second, "Idempotency violated: table count changed"


def test_migration_round_trip(db_connection, database_url: str) -> None:
    """Test that upgrade followed by downgrade leaves no artifacts."""
    # Clean slate
    run_script("db_downgrade.sh", database_url)
    
    # Apply and rollback
    run_script("db_upgrade.sh", database_url)
    run_script("db_downgrade.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    # Should only have migration tracking table if any
    assert len(tables) == 0, f"Tables remain after downgrade: {tables}"


def test_foreign_key_constraints(db_connection, database_url: str) -> None:
    """Test that foreign key constraints are properly defined."""
    run_script("db_upgrade.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name;
    """)
    
    fks = cursor.fetchall()
    assert len(fks) >= 6, f"Expected at least 6 foreign keys, got {len(fks)}"
    
    # Verify specific foreign keys
    fk_map = {(row[0], row[1]): (row[2], row[3]) for row in fks}
    
    assert fk_map.get(("coffee_runs", "initiator_user_id")) == ("users", "user_id")
    assert fk_map.get(("coffee_runs", "runner_user_id")) == ("users", "user_id")
    assert fk_map.get(("orders", "run_id")) == ("coffee_runs", "run_id")
    assert fk_map.get(("orders", "user_id")) == ("users", "user_id")


def test_indexes_exist(db_connection, database_url: str) -> None:
    """Test that required indexes are created."""
    run_script("db_upgrade.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """)
    
    indexes = cursor.fetchall()
    index_names = [row[1] for row in indexes]
    
    required_indexes = [
        "idx_users_email",
        "idx_coffee_runs_workspace",
        "idx_coffee_runs_status",
        "idx_orders_run",
        "idx_orders_user",
        "idx_user_preferences_user",
        "idx_audit_logs_timestamp",
    ]
    
    for idx in required_indexes:
        assert idx in index_names, f"Missing index: {idx}"


def test_seed_data_idempotency(db_connection, database_url: str) -> None:
    """Test that seed data can be applied multiple times safely."""
    run_script("db_upgrade.sh", database_url)
    run_script("db_seed.sh", database_url)
    
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    count_after_first = cursor.fetchone()[0]
    
    run_script("db_seed.sh", database_url)
    cursor.execute("SELECT COUNT(*) FROM users;")
    count_after_second = cursor.fetchone()[0]
    
    assert count_after_first == count_after_second, "Seed idempotency violated"
    assert count_after_first >= 10, f"Expected at least 10 users, got {count_after_first}"


def test_connection_pool_config(database_url: str) -> None:
    """Test that connection pooling parameters are reasonable."""
    # This is a smoke test; actual pooling is configured at runtime
    # We verify the URL is parseable and contains expected components
    assert "postgresql://" in database_url or "postgres://" in database_url
    
    # Attempt connection with pool-like settings
    conn = psycopg2.connect(
        database_url,
        connect_timeout=30,
        options="-c statement_timeout=30000"
    )
    conn.close()


def test_enum_type_exists(db_connection, database_url: str) -> None:
    """Test that custom ENUM types are created."""
    run_script("db_upgrade.sh", database_url
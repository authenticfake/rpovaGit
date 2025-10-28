#!/usr/bin/env bash
# CoffeeBuddy Database Upgrade Script
# Applies all *.up.sql migrations in order

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SQL_DIR="${PROJECT_ROOT}/src/storage/sql"

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env" ]; then
    export $(grep -v '^#' "${PROJECT_ROOT}/.env" | xargs)
fi

# Validate DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    exit 1
fi

echo "=== CoffeeBuddy Database Upgrade ==="
echo "SQL Directory: ${SQL_DIR}"
echo "Database URL: ${DATABASE_URL}"
echo ""

# Find all *.up.sql files and sort them
UP_FILES=$(find "${SQL_DIR}" -name "*.up.sql" | sort)

if [ -z "${UP_FILES}" ]; then
    echo "No migration files found in ${SQL_DIR}"
    exit 0
fi

# Apply each migration
for FILE in ${UP_FILES}; do
    echo "Applying: $(basename ${FILE})"
    psql "${DATABASE_URL}" -f "${FILE}" -v ON_ERROR_STOP=1
    if [ $? -eq 0 ]; then
        echo "✓ Success"
    else
        echo "✗ Failed"
        exit 1
    fi
    echo ""
done

echo "=== All migrations applied successfully ==="
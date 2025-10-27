#!/usr/bin/env bash
set -euo pipefail

# db_upgrade.sh: Apply all *.up.sql migrations in order
# Usage: ./db_upgrade.sh [DATABASE_URL]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"
DATABASE_URL="${1:-${DATABASE_URL:-}}"

if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL not set. Provide as argument or environment variable."
    echo "Usage: $0 postgresql://user:password@localhost:5432/coffeebuddy"
    exit 1
fi

echo "==> Applying migrations to: ${DATABASE_URL}"

# Find all *.up.sql files and sort them
for migration in $(find "$SQL_DIR" -name "*.up.sql" | sort); do
    echo "==> Applying: $(basename "$migration")"
    psql "$DATABASE_URL" -f "$migration" -v ON_ERROR_STOP=1
done

echo "==> All migrations applied successfully"
```

```bash
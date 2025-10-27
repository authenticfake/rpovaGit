#!/usr/bin/env bash
set -euo pipefail

# db_downgrade.sh: Rollback all *.down.sql migrations in reverse order
# Usage: ./db_downgrade.sh [DATABASE_URL]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"
DATABASE_URL="${1:-${DATABASE_URL:-}}"

if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL not set. Provide as argument or environment variable."
    echo "Usage: $0 postgresql://user:password@localhost:5432/coffeebuddy"
    exit 1
fi

echo "==> Rolling back migrations from: ${DATABASE_URL}"

# Find all *.down.sql files and sort them in reverse
for migration in $(find "$SQL_DIR" -name "*.down.sql" | sort -r); do
    echo "==> Rolling back: $(basename "$migration")"
    psql "$DATABASE_URL" -f "$migration" -v ON_ERROR_STOP=1
done

echo "==> All migrations rolled back successfully"
```

```bash
#!/usr/bin/env bash
set -euo pipefail

# db_seed.sh: Apply seed data (idempotent)
# Usage: ./db_seed.sh [DATABASE_URL]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="${SCRIPT_DIR}/../src/storage/seed/seed.sql"
DATABASE_URL="${1:-${DATABASE_URL:-}}"

if [[ -z "$DATABASE_URL" ]]; then
    echo "Error: DATABASE_URL not set. Provide as argument or environment variable."
    echo "Usage: $0 postgresql://user:password@localhost:5432/coffeebuddy"
    exit 1
fi

echo "==> Applying seed data to: ${DATABASE_URL}"
psql "$DATABASE_URL" -f "$SEED_FILE" -v ON_ERROR_STOP=1
echo "==> Seed data applied successfully"
```

```python
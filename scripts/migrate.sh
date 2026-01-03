#!/bin/bash

# JARVIS Database Migration Script
# Runs all SQL migrations in order

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-jarvis}"
DB_USER="${DB_USER:-jarvis}"
DB_PASSWORD="${DB_PASSWORD:-jarvis}"

MIGRATIONS_DIR="$(dirname "$0")/../infrastructure/migrations"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  J.A.R.V.I.S. Database Migration                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed${NC}"
    echo "Please install PostgreSQL client tools"
    exit 1
fi

# Create migration tracking table if it doesn't exist
echo "Checking migration tracking table..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
" 2>/dev/null || {
    echo -e "${RED}Error: Could not connect to database${NC}"
    echo "Make sure PostgreSQL is running and credentials are correct"
    exit 1
}

echo ""
echo "Running migrations..."
echo ""

# Get list of migration files
MIGRATIONS=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)

if [ -z "$MIGRATIONS" ]; then
    echo -e "${YELLOW}No migration files found in $MIGRATIONS_DIR${NC}"
    exit 0
fi

APPLIED=0
SKIPPED=0

for migration in $MIGRATIONS; do
    MIGRATION_NAME=$(basename "$migration")

    # Check if migration has already been applied
    ALREADY_APPLIED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
        SELECT COUNT(*) FROM schema_migrations WHERE migration_name = '$MIGRATION_NAME';
    " 2>/dev/null | xargs)

    if [ "$ALREADY_APPLIED" = "1" ]; then
        echo -e "${YELLOW}⏭  Skipping $MIGRATION_NAME (already applied)${NC}"
        ((SKIPPED++))
        continue
    fi

    echo -e "Applying $MIGRATION_NAME..."

    # Run the migration
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration" 2>&1; then
        # Record the migration
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
            INSERT INTO schema_migrations (migration_name) VALUES ('$MIGRATION_NAME');
        " 2>/dev/null

        echo -e "${GREEN}✓  Applied $MIGRATION_NAME${NC}"
        ((APPLIED++))
    else
        echo -e "${RED}✗  Failed to apply $MIGRATION_NAME${NC}"
        exit 1
    fi
done

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Migration Complete                                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo -e "Applied: ${GREEN}$APPLIED${NC}"
echo -e "Skipped: ${YELLOW}$SKIPPED${NC}"
echo ""

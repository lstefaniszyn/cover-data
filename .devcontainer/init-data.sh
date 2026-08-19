#!/usr/bin/env bash
set -e

echo "🗄️  Initializing PostgreSQL database for App..."

# Check if non-root user and password environment variables are set
if [ -n "${POSTGRES_NON_ROOT_USER:-}" ] && [ -n "${POSTGRES_NON_ROOT_PASSWORD:-}" ]; then
  echo "👤 Creating non-root user '${POSTGRES_NON_ROOT_USER}' with full database privileges..."

  # Connect to PostgreSQL as root (POSTGRES_USER) on POSTGRES_DB
  cat <<EOSQL | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
DO
\$\$
BEGIN
  -- Create user if it doesn't exist. Use quotes to preserve case in the username.
  IF NOT EXISTS (
    SELECT FROM pg_catalog.pg_roles
    WHERE rolname = '${POSTGRES_NON_ROOT_USER}'
  ) THEN
    EXECUTE format('CREATE USER %I WITH PASSWORD %L',
      '${POSTGRES_NON_ROOT_USER}',
      '${POSTGRES_NON_ROOT_PASSWORD}'
    );
    RAISE NOTICE 'User % created successfully', '${POSTGRES_NON_ROOT_USER}';
  ELSE
    RAISE NOTICE 'User % already exists', '${POSTGRES_NON_ROOT_USER}';
  END IF;
END
\$\$;

-- Grant all privileges on the database to the non-root user
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO "${POSTGRES_NON_ROOT_USER}";

-- Grant privileges on the public schema to allow the user to create tables, etc.
GRANT ALL PRIVILEGES ON SCHEMA public TO "${POSTGRES_NON_ROOT_USER}";

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${POSTGRES_NON_ROOT_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${POSTGRES_NON_ROOT_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO "${POSTGRES_NON_ROOT_USER}";

-- Make the non-root user the owner of the public schema
ALTER SCHEMA public OWNER TO "${POSTGRES_NON_ROOT_USER}";
EOSQL

  echo "✅ Database initialization complete!"
  echo "   User: ${POSTGRES_NON_ROOT_USER}"
  echo "   Database: ${POSTGRES_DB}"
  echo "   Privileges: GRANTED"
else
  echo "⚠️  Warning: POSTGRES_NON_ROOT_USER or POSTGRES_NON_ROOT_PASSWORD not provided!"
  echo "   Skipping non-root user creation."
fi

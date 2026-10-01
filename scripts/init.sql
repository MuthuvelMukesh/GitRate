-- GitRate database bootstrap.
-- Referenced by docker-compose.yml (mounted into /docker-entrypoint-initdb.d).
-- Schema objects are created by Alembic (`alembic upgrade head`), this file only
-- prepares the database and the extensions the application relies on.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Read-only role for reporting/BI consumers (tenant isolation is enforced in the
-- application layer and by row-level filtering; this role cannot write).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gitrate_readonly') THEN
        CREATE ROLE gitrate_readonly NOLOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE gitrate_audit TO gitrate_readonly;
GRANT USAGE ON SCHEMA public TO gitrate_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO gitrate_readonly;

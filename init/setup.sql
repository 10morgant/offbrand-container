-- ==========================================================
-- Configuration
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ==========================================================
-- Create application role
-- ==========================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles
        WHERE rolname = 'appuser'
    ) THEN
        CREATE ROLE appuser
            LOGIN
            PASSWORD 'StrongPassword123!';
    END IF;
END
$$;

-- ==========================================================
-- Create databases
-- ==========================================================

CREATE DATABASE docker OWNER appuser;
CREATE DATABASE npm OWNER appuser;
CREATE DATABASE python OWNER appuser;
CREATE DATABASE golang OWNER appuser;
CREATE DATABASE cargo OWNER appuser;

-- ==========================================================
-- Grant database privileges
-- ==========================================================

GRANT ALL PRIVILEGES ON DATABASE docker TO appuser;
GRANT ALL PRIVILEGES ON DATABASE npm TO appuser;
GRANT ALL PRIVILEGES ON DATABASE python TO appuser;
GRANT ALL PRIVILEGES ON DATABASE golang TO appuser;
GRANT ALL PRIVILEGES ON DATABASE cargo TO appuser;
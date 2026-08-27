-- Local dev database setup for walkrun (run once as the postgres superuser).
-- Mirrors the credentials in docker-compose.yml / backend/.env.
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'walkrun') THEN
      CREATE ROLE walkrun LOGIN PASSWORD 'walkrun_dev_pw';
   END IF;
END
$$;

SELECT 'CREATE DATABASE walkrun OWNER walkrun'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'walkrun')\gexec

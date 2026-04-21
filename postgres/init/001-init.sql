-- Note:
-- The official postgres image creates POSTGRES_DB during first-time initialization.
-- Because of that, this script only creates/updates the application role and grants access.

DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'wifi_app'
   ) THEN
      CREATE ROLE wifi_app LOGIN PASSWORD 'R8@wF3!nK6#qP1$vT9mX2h';
   ELSE
      ALTER ROLE wifi_app WITH LOGIN PASSWORD 'R8@wF3!nK6#qP1$vT9mX2h';
   END IF;
END
$$;

GRANT CONNECT ON DATABASE wifisurvey TO wifi_app;

\connect wifisurvey

GRANT USAGE, CREATE ON SCHEMA public TO wifi_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wifi_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO wifi_app;

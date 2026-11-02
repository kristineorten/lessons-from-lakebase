"""Give the app's service principal what it needs in Postgres.

Run this before adding the database resource to the app. The role must be created
with databricks_create_role, or GRANT ... TO authenticator fails with permission
denied. A role made by the app resource or in the UI cannot be granted. The app
reuses the role when the resource is added afterwards.

Run it again after adding synced tables: they are created by the pipeline's own
role, so default privileges do not reach them.
"""
from common import APP_NAME, SCHEMA, cli, postgres

app_role = cli("apps", "get", APP_NAME)["service_principal_client_id"]

with postgres() as conn:
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_role,)).fetchone()
    if not exists:
        conn.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
        conn.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", (app_role,))
    conn.execute(f'GRANT "{app_role}" TO authenticator')
    conn.execute(f'GRANT USAGE ON SCHEMA {SCHEMA} TO "{app_role}"')
    conn.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO "{app_role}"')
    print("app role ready")

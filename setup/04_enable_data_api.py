"""Turn on the Data API with one REST call, and refresh its schema cache."""
from common import BRANCH, SCHEMA, cli, cli_json, postgres

path = f"/api/2.0/postgres/{BRANCH}/databases/databricks-postgres/data-api"
if cli("api", "get", path, check=False):
    print("Data API: already enabled")
else:
    body = {"spec": {"db_schemas": ["public", SCHEMA], "server_timing_enabled": True}}
    cli_json("api", "post", path, body=body)
    print("Data API: enabled")

with postgres() as conn:
    conn.execute("NOTIFY pgrst, 'reload schema'")
print("schema cache refresh requested")

"""Register the Lakebase database in Unity Catalog, so Databricks SQL can read Ingrid's decisions live."""
from common import BRANCH, DATABASE, LAKEBASE_CATALOG, cli, cli_json

if cli("postgres", "get-catalog", f"catalogs/{LAKEBASE_CATALOG}", check=False):
    print(f"catalog {LAKEBASE_CATALOG}: already registered")
else:
    body = {"spec": {"branch": BRANCH, "postgres_database": DATABASE}}
    cli_json("postgres", "create-catalog", LAKEBASE_CATALOG, body=body)
    print(f"catalog {LAKEBASE_CATALOG}: registered")

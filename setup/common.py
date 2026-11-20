"""Shared helpers for the setup scripts. Settings come from .env."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


ENV = load_env()
CATALOG = ENV["CATALOG"]
LAKEBASE_CATALOG = ENV.get("LAKEBASE_CATALOG") or "lessons_from_lakebase_pg"
PROJECT_ID = ENV.get("PROJECT_ID") or "lessons-from-lakebase-demo"
PROJECT = f"projects/{PROJECT_ID}"
BRANCH = f"{PROJECT}/branches/production"
ENDPOINT = f"{BRANCH}/endpoints/primary"
DATABASE = "databricks_postgres"
APP_NAME = "lessons-from-lakebase-app"
SCHEMA = "lessons_from_lakebase"
DATABRICKS = ENV.get("DATABRICKS_CLI") or shutil.which("databricks")


def cli(*args, check=True):
    cmd = [DATABRICKS, *args, "--profile", ENV["DATABRICKS_PROFILE"], "-o", "json"]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        if check:
            raise SystemExit(done.stderr.strip() or done.stdout.strip())
        return None
    return json.loads(done.stdout) if done.stdout.strip() else {}


def cli_json(*args, body, check=True):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f)
    try:
        return cli(*args, "--json", f"@{f.name}", check=check)
    finally:
        os.unlink(f.name)


def warehouse_id():
    warehouses = cli("warehouses", "list")
    serverless = [w for w in warehouses if w.get("enable_serverless_compute")]
    return (serverless or warehouses)[0]["id"]


def sql(statement, warehouse):
    body = {"statement": statement, "warehouse_id": warehouse, "wait_timeout": "50s"}
    result = cli_json("api", "post", "/api/2.0/sql/statements", body=body)
    while result["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        result = cli("api", "get", f"/api/2.0/sql/statements/{result['statement_id']}")
    if result["status"]["state"] != "SUCCEEDED":
        raise SystemExit(result["status"])
    return result


def postgres(endpoint=ENDPOINT):
    """Connect to Lakebase as the logged-in user."""
    host = cli("postgres", "get-endpoint", endpoint)["status"]["hosts"]["host"]
    token = cli("postgres", "generate-database-credential", endpoint)["token"]
    user = cli("current-user", "me")["userName"]
    return psycopg.connect(
        host=host, dbname=DATABASE, user=user, password=token, sslmode="require", autocommit=True
    )

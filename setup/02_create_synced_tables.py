"""Sync the tables to Lakebase, sharing one pipeline. Safe to run again.

Each synced table is declared on its own: there is no schema-level option.
The first table creates the pipeline, and the others join it. A table that joins
a triggered pipeline stays offline until the pipeline next runs.
"""
import time

from common import BRANCH, CATALOG, DATABASE, SCHEMA, cli, cli_json

TABLES = [
    ("accounts", ["account_id"]),
    ("account_revenue", ["account_id", "month"]),
    ("account_support", ["account_id"]),
]


def wait_online(name, limit=600):
    start = time.time()
    while time.time() - start < limit:
        status = cli("postgres", "get-synced-table", f"synced_tables/{name}")["status"]
        state = status["detailed_state"]
        if state.startswith("SYNCED_TABLE_ONLINE"):
            return status
        if "FAILED" in state:
            raise SystemExit(status)
        time.sleep(10)
    raise SystemExit(f"timed out waiting for {name}")


def run_pipeline(pipeline_id):
    while cli("pipelines", "get", pipeline_id).get("state") != "IDLE":
        time.sleep(5)
    cli("pipelines", "start-update", pipeline_id)


pipeline = None
for table, keys in TABLES:
    name = f"{CATALOG}.{SCHEMA}.{table}_synced"
    existing = cli("postgres", "get-synced-table", f"synced_tables/{name}", check=False)
    if existing:
        pipeline = pipeline or existing["status"].get("pipeline_id")
        print(f"{name}: already exists")
        continue
    spec = {
        "source_table_full_name": f"{CATALOG}.{SCHEMA}.{table}",
        "branch": BRANCH,
        "postgres_database": DATABASE,
        "primary_key_columns": keys,
        "scheduling_policy": "TRIGGERED",
        "create_database_objects_if_missing": True,
    }
    joins = bool(pipeline)
    if joins:
        spec["existing_pipeline_id"] = pipeline
    else:
        spec["new_pipeline_spec"] = {"storage_catalog": CATALOG, "storage_schema": SCHEMA}
    cli_json("postgres", "create-synced-table", name, body={"spec": spec})
    if joins:
        run_pipeline(pipeline)
    status = wait_online(name)
    pipeline = pipeline or status["pipeline_id"]
    print(f"{name}: online, pipeline {status['pipeline_id']}")

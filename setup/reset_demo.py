"""Put the demo back to its starting point, before or after a run-through.

Clears Ingrid's decisions, restores the three lakehouse tables to the seed data,
and syncs them to Lakebase. Branches are listed, not deleted, because you may
have made them on purpose.
"""
import time

from common import BRANCH, PROJECT, cli, postgres, warehouse_id
from demo_data import ACCOUNTS, row_counts, write_rows

with postgres() as conn:
    conn.execute("DELETE FROM desk.decisions")
print("decisions cleared")

wh = warehouse_id()
write_rows(wh, restore=True)
print("lakehouse tables restored to the seed data")
row_counts(wh)

branches = cli("postgres", "list-branches", PROJECT)
branches = branches.get("branches", []) if isinstance(branches, dict) else branches
for branch in branches:
    if branch["name"] != BRANCH:
        print(f"branch left from a run-through: {branch['name']}")
        print(f"  delete it with: databricks postgres delete-branch {branch['name']}")

synced = cli("postgres", "get-synced-table", f"synced_tables/{ACCOUNTS}_synced")
pipeline = synced["status"]["pipeline_id"]
while cli("pipelines", "get", pipeline).get("state") != "IDLE":
    time.sleep(5)
cli("pipelines", "start-update", pipeline)
print("sync started. Refresh the app in about a minute.")

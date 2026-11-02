"""Put the demo back to its starting point, before a rehearsal or a recording."""
import time

from common import CATALOG, SCHEMA, cli, postgres, sql, warehouse_id

ACCOUNTS = f"{CATALOG}.{SCHEMA}.accounts"

with postgres() as conn:
    conn.execute("DELETE FROM desk.decisions")
print("decisions cleared")

sql(f"""
UPDATE {ACCOUNTS}
SET risk_score = 57,
    risk_reason = 'Late payments on the last two invoices',
    updated_at = current_timestamp()
WHERE account_id = 5
""", warehouse_id())

synced = cli("postgres", "get-synced-table", f"synced_tables/{ACCOUNTS}_synced")
pipeline = synced["status"]["pipeline_id"]
while cli("pipelines", "get", pipeline).get("state") != "IDLE":
    time.sleep(5)
cli("pipelines", "start-update", pipeline)
print("sync started. Refresh the app in about a minute.")

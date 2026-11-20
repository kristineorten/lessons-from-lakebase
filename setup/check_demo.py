"""Check the deployed demo from end to end, then remove the test decision."""
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from common import APP_NAME, CATALOG, LAKEBASE_CATALOG, SCHEMA, cli, postgres, sql, warehouse_id

MARKER = "Automated check, safe to delete"
ACCOUNT = 4

base = cli("apps", "get", APP_NAME)["url"]
token = cli("auth", "token")["access_token"]


def get(path, data=None, headers=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(
        base + path, data=body, headers={"Authorization": f"Bearer {token}", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""


status, html = get("/")
print("renewals page:", status, "customers:", len(re.findall(r'href="/customer/\d+"', html)))
status, html = get(f"/customer/{ACCOUNT}")
print("customer page:", status, "order history:", '"orders-data"' in html)

times = []
for _ in range(8):
    status, html = get("/data-api")
    times.append(int(re.search(r'tile-value">(\d+) ms', html).group(1)))
print("data api page:", status, "round trip ms:", sorted(times)[len(times) // 2], "median")

good = {"decision": "Renew with a discount", "reason": MARKER}
path = f"/customer/{ACCOUNT}/decision"
print("cross-site post refused:", get(path, good, {"Sec-Fetch-Site": "cross-site"})[0] == 403)
print("unknown decision refused:", get(path, {"decision": "x", "reason": "y"})[0] == 400)
print("unknown customer refused:", get("/customer/9999/decision", good)[0] == 404)

start = time.time()
get(path, good)
query = f"""
SELECT a.account_name, d.decision, a.annual_value_nok
FROM {LAKEBASE_CATALOG}.desk.decisions AS d
JOIN {CATALOG}.{SCHEMA}.accounts AS a ON a.account_id = d.account_id
WHERE d.reason = '{MARKER}'
"""
rows = sql(query, warehouse_id()).get("result", {}).get("data_array")
print(f"read from Databricks SQL after {time.time() - start:.1f}s:", rows)

with postgres() as conn:
    gone = conn.execute("DELETE FROM desk.decisions WHERE reason = %s", (MARKER,)).rowcount
print("test decision removed:", gone)
sys.exit(0 if rows else 1)

"""Run the app locally against Lakebase as yourself, to check the pages.

Writes are not exercised here. The Data API page shows an error locally, because
the project owner cannot use the Data API.
"""
import os
import subprocess
import sys

from common import DATABASE, DATABRICKS, ENDPOINT, ENV, ROOT, cli

host = cli("postgres", "get-endpoint", ENDPOINT)["status"]["hosts"]["host"]
os.environ.update(
    {
        "PATH": os.path.dirname(DATABRICKS) + os.pathsep + os.environ["PATH"],
        "DATABRICKS_CONFIG_PROFILE": ENV["DATABRICKS_PROFILE"],
        "ENDPOINT_NAME": ENDPOINT,
        "PGHOST": host,
        "PGDATABASE": DATABASE,
        "PGUSER": cli("current-user", "me")["userName"],
    }
)
subprocess.run(
    [sys.executable, "-m", "flask", "--app", "app.py", "run", "--port", "8899"],
    cwd=ROOT / "app",
    check=True,
)

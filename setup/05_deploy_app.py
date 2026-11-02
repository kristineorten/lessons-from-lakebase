"""Upload the app and deploy it."""
from common import APP_NAME, DATABRICKS, ENV, ROOT, cli

import subprocess

user = cli("current-user", "me")["userName"]
target = f"/Workspace/Users/{user}/lessons-from-lakebase/app"
profile = ["--profile", ENV["DATABRICKS_PROFILE"]]

subprocess.run([DATABRICKS, "workspace", "mkdirs", target, *profile], check=True)
subprocess.run(
    [DATABRICKS, "sync", str(ROOT / "app"), target, "--full", *profile],
    check=True, capture_output=True,
)
result = cli("apps", "deploy", APP_NAME, "--source-code-path", target)
print(result["status"]["state"], "-", result["status"]["message"])
print(cli("apps", "get", APP_NAME)["url"])

"""Write app.yaml for your project, upload the app and deploy it."""
from common import APP_NAME, DATABRICKS, ENDPOINT, ENV, ROOT, cli

import subprocess

# app.yaml is generated, so the endpoint always matches PROJECT_ID in .env.
(ROOT / "app" / "app.yaml").write_text(
    "command: ['gunicorn', 'app:app', '--bind', '0.0.0.0:8000', '--workers', '1', '--threads', '4']\n"
    "\n"
    "env:\n"
    "  - name: ENDPOINT_NAME\n"
    f"    value: '{ENDPOINT}'\n",
    encoding="utf-8",
)

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

# Lessons from Building Operational Solutions with Lakebase

Demo material for a talk at the Databricks Oslo User Group, 19 November 2026.

**Renewal review** is a small app that shows what Lakebase, the managed Postgres in Databricks, can do.

Ingrid, a fictional account executive at a wholesaler, reviews every customer coming up for renewal and decides what to do. She cannot do that from the app's own data, and Finance needs her decisions straight away:

1. **The history is in the lakehouse.** The company moved to a new ERP last year, and older orders were not migrated, so they exist only there, next to tickets from the support system and a risk score.
2. **Lakebase serves it to the app.** Synced tables copy the data to Postgres for fast reads.
3. **Ingrid decides.** Her decisions go straight into an ordinary Postgres table.
4. **Finance sees it at once.** The forecast in Databricks reads her decisions live, with no pipeline in between.

All companies, people and figures are invented.

## Run it yourself

You run this in **your own Databricks workspace, with your own account**. The repo contains no access to anyone else's workspace, and nothing here connects to one until you log in yourself.

You need:

- A Databricks workspace with Lakebase, Databricks Apps and serverless compute
- Permission to create a Lakebase project, an app and a schema
- The [Databricks CLI](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/cli/install), version 1.0 or later
- Python 3.10 or later

Running this costs money in a paid workspace, so see [Clean up](#clean-up). It has been tested on Azure Databricks only, not on AWS, GCP or Databricks Free Edition. Lakebase is not available in every region: check [region availability](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/manage-projects#availability) first.

### Steps

Create your settings and install what the scripts need:

```bash
databricks auth login --host <your-workspace-url> --profile my-profile
cp .env.example .env   # then set DATABRICKS_PROFILE and CATALOG
python -m venv .venv
.venv/bin/pip install -r setup/requirements.txt   # on Windows: .venv\Scripts\pip
```

Use the Python in `.venv` for all the scripts below.

Create the Lakebase project. The settings below keep the compute small. The commands use the project id `lessons-from-lakebase-demo`. If you choose another one, set `PROJECT_ID` in `.env` and use your id in the commands too:

```bash
databricks postgres create-project lessons-from-lakebase-demo --profile my-profile --json '{
  "spec": {
    "display_name": "Lessons from Lakebase demo",
    "pg_version": 17,
    "default_endpoint_settings": {
      "autoscaling_limit_min_cu": 0.5,
      "autoscaling_limit_max_cu": 2,
      "suspend_timeout_duration": "300s"
    }
  }
}'
```

Add the data and sync it:

```bash
python setup/01_seed_lakehouse.py
python setup/02_create_synced_tables.py
```

Create the app without a database resource. The order matters here, because the app's Postgres role must be created in SQL first:

```bash
databricks apps create --profile my-profile --json '{"name": "lessons-from-lakebase-app"}'
python setup/03_configure_app_access.py
```

Add the database resource, then enable the Data API and deploy:

```bash
databricks apps update lessons-from-lakebase-app --profile my-profile --json '{
  "name": "lessons-from-lakebase-app",
  "resources": [{
    "name": "postgres",
    "postgres": {
      "branch": "projects/lessons-from-lakebase-demo/branches/production",
      "database": "projects/lessons-from-lakebase-demo/branches/production/databases/databricks-postgres",
      "permission": "CAN_CONNECT_AND_CREATE"
    }
  }]
}'
python setup/04_enable_data_api.py
python setup/05_deploy_app.py
```

`05_deploy_app.py` writes `app/app.yaml` for your project before it uploads the app.

Register the Lakebase database in Unity Catalog, so Databricks SQL can read Ingrid's decisions live. Then check the whole demo from end to end:

```bash
python setup/06_register_catalog.py
python setup/check_demo.py
```

[docs/demo-script.md](docs/demo-script.md) walks through the demo. `python setup/reset_demo.py` puts it back to its starting point.

## Clean up

Stop the app when you are done, and turn off anything that runs on a schedule:

```bash
databricks apps stop lessons-from-lakebase-app --profile my-profile
```

The Lakebase compute suspends by itself after five minutes without queries, even while the app runs, because the app keeps no idle connections open. The app itself is billed for as long as it runs. To remove everything, delete the app, the synced tables, the Lakebase catalog, the Unity Catalog schema, and then the Lakebase project.

## What is where

| Path | What it is |
|---|---|
| `app/` | The Databricks App: Flask, Postgres and Chart.js |
| `setup/` | Numbered scripts that build the demo |
| `docs/demo-script.md` | The steps of the live demo |

## Notes

- Lakebase changes quickly, and parts of this use Beta features. Check the [release notes](https://learn.microsoft.com/en-us/azure/databricks/release-notes/lakebase/) if a step fails.
- Chart.js 4.4.9 is included in `app/static/vendor` under its MIT licence.
- This is a demo, not a production app. Everyone with access to the app acts as Ingrid, because it does not record who is signed in.
- This is a personal project. It is not an official Databricks product.
- The code is under the [MIT licence](LICENSE).

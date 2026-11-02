# Demo script

About 15 minutes. Start the app, then open it and the Data API page once before you begin. That wakes the compute, so the first slow call is not the one the audience sees.

Keep bookmarks to your own project and schema, so you never browse workspace lists on screen.

The story: a wholesaler sells to businesses on yearly contracts. Before a contract runs out, Ingrid, the account executive, decides whether to renew it and on what terms. The company moved to a new ERP last year and older orders were not migrated, so the full history exists only in the lakehouse. Finance needs her decisions in the forecast at once. Her app is a Databricks App here, but it could be any application.

Reset first with `python setup/reset_demo.py`.

## 1. Ingrid's job (2 min)

1. Open the app and read the question at the top.
2. Walk through **Why this needs more than one database**.
3. Open **Nordkapp Foods**. Point out where each panel comes from: order history from the old and new ERP, tickets from the support system, and the score from the lakehouse.
4. Choose a decision, give a reason and save.
5. Open the table `desk.decisions` in the Lakebase project and show the row.

Point: the app has no stored database password. It gets short-lived tokens by itself.

## 2. The lakehouse updates the app (3 min)

In Databricks SQL, raise the risk of another customer:

```sql
UPDATE <catalog>.lessons_from_lakebase.accounts
SET risk_score = 88,
    risk_reason = 'Competitor offer confirmed',
    updated_at = current_timestamp()
WHERE account_id = 5;
```

Run the sync from the synced table's **Overview** tab with **Sync now**, then refresh the app. Bryggen Bakeries changes to high risk.

Point: reads are fast, but freshness follows the sync. Rehearsal took about 43 seconds.

## 3. The same data over REST (2 min)

Open the **Data API** page. Show the URL, the milliseconds and the result.

Point: a partner portal or another system could read this with no backend code. Rehearsal median was about 50 ms.

## 4. Branch the database (5 min)

1. In the Lakebase project, create a branch from `production`. It takes a few seconds, with all the data.
2. On the branch, run something you would not dare run in production:

   ```sql
   DROP TABLE desk.decisions;
   ```

3. Show the app, which still works, because it uses `production`.
4. Show the schema diff against `production`.
5. Delete the branch.

Point: a full copy to experiment on, in seconds.

## 5. Finance sees it at once (3 min)

Save a new decision in the app, then query the forecast straight away in Databricks SQL, with no pipeline in between:

```sql
SELECT d.decision, count(*) AS customers, sum(a.annual_value_nok) AS annual_value_nok
FROM <lakebase_catalog>.desk.decisions AS d
JOIN <catalog>.lessons_from_lakebase.accounts AS a USING (account_id)
GROUP BY d.decision
ORDER BY annual_value_nok DESC;
```

Point: this is the vision. Change it in the app, open Databricks, and it is already there.

## Afterwards

Reset the demo:

```sql
UPDATE <catalog>.lessons_from_lakebase.accounts
SET risk_score = 57,
    risk_reason = 'Late payments on the last two invoices',
    updated_at = current_timestamp()
WHERE account_id = 5;
```

Then sync, and stop the app.

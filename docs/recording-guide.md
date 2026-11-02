# Recording the backup video

The video is the fallback if the live demo fails. Record it as five short clips, one per demo step, so you can jump to the step that failed instead of restarting.

## Before you record

1. Run `python setup/reset_demo.py`, and refresh the app after a minute.
2. Open the app and the Data API page once, to wake everything up.
3. Use a clean browser profile, signed in only to the demo workspace.
4. Set the browser window to 1920 × 1080, at 125% zoom, in light mode so it reads well on a projector.
5. Open each tab in advance from a bookmark to your own project, schema and SQL query. Never open a workspace list.
6. Close notifications and hide bookmarks with personal or client names.

## The clips

No sound: you narrate live. Pause on each result for about three seconds.

| Clip | Shows | Length |
|---|---|---|
| `demo-1-decide.mp4` | Open a customer, save a decision, show the row in Lakebase | 60 s |
| `demo-2-sync.mp4` | Raise a risk score, run the sync, see it change in the app. Trim the wait | 45 s |
| `demo-3-data-api.mp4` | Open the Data API page and refresh once | 30 s |
| `demo-4-branch.mp4` | Create a branch, drop a table, show the schema diff, delete the branch | 90 s |
| `demo-5-forecast.mp4` | Save a decision, run the forecast query in Databricks SQL | 45 s |

## Recording and checking

Use Windows Snipping Tool (screen recording) or OBS Studio. Export as MP4, H.264, 1080p.

Before using a clip, watch it to the end and check that it shows no email address, no other team's work and no client name.

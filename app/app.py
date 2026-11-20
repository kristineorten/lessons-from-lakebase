"""Renewal review: a Databricks App on Lakebase. All data and companies are invented."""
import os
import time

import psycopg
import requests
from databricks.sdk import WorkspaceClient
from flask import Flask, abort, redirect, render_template, request, url_for
from psycopg_pool import ConnectionPool

app = Flask(__name__)
w = WorkspaceClient()

HIGH_RISK = 70
MEDIUM_RISK = 40
DECISIONS = ["Renew as is", "Renew with a discount", "Escalate to manager", "Will not renew"]
MAX_REASON = 500
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


@app.before_request
def block_cross_site_writes():
    """Browsers mark forged form posts, so a page elsewhere cannot save a decision."""
    if request.method == "POST":
        if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            abort(403)


@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


class OAuthConnection(psycopg.Connection):
    """Fetches a fresh Lakebase token for every new connection."""

    @classmethod
    def connect(cls, conninfo="", **kwargs):
        credential = w.postgres.generate_database_credential(endpoint=os.environ["ENDPOINT_NAME"])
        kwargs["password"] = credential.token
        return super().connect(conninfo, **kwargs)


pool = ConnectionPool(
    conninfo=(
        f"dbname={os.environ['PGDATABASE']} user={os.environ['PGUSER']} "
        f"host={os.environ['PGHOST']} port={os.environ.get('PGPORT', '5432')} "
        f"sslmode={os.environ.get('PGSSLMODE', 'require')}"
    ),
    connection_class=OAuthConnection,
    # No connection is kept open when idle, so Lakebase can scale to zero while the app runs.
    min_size=0,
    max_size=5,
    max_idle=120,
    open=True,
)

with pool.connection() as conn:
    conn.execute("CREATE SCHEMA IF NOT EXISTS desk")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS desk.decisions (
            id SERIAL PRIMARY KEY,
            account_id INT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT NOT NULL,
            decided_by TEXT NOT NULL DEFAULT 'Ingrid',
            decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

ACCOUNTS = """
    SELECT a.account_id, a.account_name, a.segment, a.annual_value_nok, a.risk_score,
           a.renewal_date, a.risk_reason, a.updated_at, s.open_tickets, s.tickets_90_days,
           d.decision
    FROM lessons_from_lakebase.accounts_synced AS a
    JOIN lessons_from_lakebase.account_support_synced AS s USING (account_id)
    LEFT JOIN LATERAL (
        SELECT decision FROM desk.decisions
        WHERE account_id = a.account_id ORDER BY decided_at DESC LIMIT 1
    ) AS d ON true
"""
ACCOUNT_COLUMNS = [
    "id", "name", "segment", "value", "risk", "renewal", "reason", "updated",
    "open_tickets", "tickets_90", "decision",
]


def risk_level(score):
    if score >= HIGH_RISK:
        return "high"
    return "medium" if score >= MEDIUM_RISK else "low"


def as_account(row):
    account = dict(zip(ACCOUNT_COLUMNS, row))
    account["level"] = risk_level(account["risk"])
    return account


def compact(value):
    return f"{value / 1_000_000:.1f}M"


app.jinja_env.filters["compact"] = compact
app.jinja_env.filters["spaced"] = lambda value: f"{value:,}".replace(",", " ")


@app.get("/")
def index():
    with pool.connection() as conn:
        accounts = [
            as_account(row)
            for row in conn.execute(ACCOUNTS + " ORDER BY d.decision IS NOT NULL, a.renewal_date")
        ]
        decided_today = conn.execute(
            "SELECT count(DISTINCT account_id) FROM desk.decisions "
            "WHERE decided_at >= date_trunc('day', now())"
        ).fetchone()[0]

    undecided = [a for a in accounts if not a["decision"]]
    open_at_risk = [a for a in undecided if a["risk"] >= MEDIUM_RISK]
    segments = {}
    for customer in open_at_risk:
        segments[customer["segment"]] = segments.get(customer["segment"], 0) + customer["value"]
    ranked = sorted(segments.items(), key=lambda item: item[1], reverse=True)
    return render_template(
        "index.html",
        accounts=accounts,
        to_review=len(undecided),
        open_at_risk=len(open_at_risk),
        value_open=sum(a["value"] for a in open_at_risk),
        decided_today=decided_today,
        segments=[{"label": k, "value": v} for k, v in ranked],
    )


@app.get("/customer/<int:account_id>")
def customer(account_id):
    with pool.connection() as conn:
        rows = conn.execute(ACCOUNTS + " WHERE a.account_id = %s", (account_id,)).fetchall()
        if not rows:
            abort(404)
        orders = conn.execute(
            "SELECT month, revenue_nok FROM lessons_from_lakebase.account_revenue_synced "
            "WHERE account_id = %s ORDER BY month",
            (account_id,),
        ).fetchall()
        history = conn.execute(
            "SELECT decision, reason, decided_by, decided_at FROM desk.decisions "
            "WHERE account_id = %s ORDER BY decided_at DESC",
            (account_id,),
        ).fetchall()
    return render_template(
        "customer.html",
        account=as_account(rows[0]),
        orders=[{"label": m.strftime("%b %y"), "value": v} for m, v in orders],
        history=history,
        decisions=DECISIONS,
    )


@app.post("/customer/<int:account_id>/decision")
def add_decision(account_id):
    decision = request.form.get("decision", "")
    reason = request.form.get("reason", "").strip()
    if decision not in DECISIONS or not 1 <= len(reason) <= MAX_REASON:
        abort(400)
    with pool.connection() as conn:
        known = conn.execute(
            "SELECT 1 FROM lessons_from_lakebase.accounts_synced WHERE account_id = %s",
            (account_id,),
        ).fetchone()
        if not known:
            abort(404)
        conn.execute(
            "INSERT INTO desk.decisions (account_id, decision, reason) VALUES (%s, %s, %s)",
            (account_id, decision, reason),
        )
    return redirect(url_for("index"))


@app.get("/data-api")
def data_api():
    params = {
        "select": "account_name,risk_score,renewal_date",
        "risk_score": f"gte.{HIGH_RISK}",
        "order": "risk_score.desc",
    }
    base = f"https://{os.environ['PGHOST']}/api/2.0/workspace/{w.get_workspace_id()}/rest"
    url = f"{base}/{os.environ['PGDATABASE']}/lessons_from_lakebase/accounts_synced"
    headers = w.config.authenticate()
    runs = []
    for _ in range(3):
        start = time.perf_counter()
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        runs.append(round((time.perf_counter() - start) * 1000))
    if not resp.ok:
        app.logger.warning("Data API returned %s: %s", resp.status_code, resp.text)
    return render_template(
        "data_api.html",
        query="&".join(f"{k}={v}" for k, v in params.items()),
        elapsed=runs[-1],
        status=resp.status_code,
        rows=resp.json() if resp.ok else [],
    )

"""The synthetic demo data, shared by the seed and reset scripts. All companies are invented."""
import random
from datetime import date

from common import CATALOG, SCHEMA, sql

ACCOUNTS = f"{CATALOG}.{SCHEMA}.accounts"
REVENUE = f"{CATALOG}.{SCHEMA}.account_revenue"
SUPPORT = f"{CATALOG}.{SCHEMA}.account_support"

# Columns: id, name, segment, annual value, risk score, days to renewal, reason for the score.
CUSTOMERS = [
    (1, "Tindefjell Transport", "Logistics", 4200000, 82, 38, "Order volume down 31% since spring"),
    (2, "Havblikk Hotels", "Hospitality", 2850000, 74, 21, "Support tickets doubled this quarter"),
    (3, "Solglott Retail", "Retail", 3100000, 68, 64, "Two key contacts have left"),
    (4, "Nordkapp Foods", "Manufacturing", 5400000, 61, 85, "Asked a competitor for a quote"),
    (5, "Bryggen Bakeries", "Retail", 1250000, 57, 120, "Late payments on the last two invoices"),
    (6, "Fjordglott Cabins", "Hospitality", 980000, 52, 47, "Usage down after the season"),
    (7, "Lysbakken Tools", "Manufacturing", 2300000, 44, 150, "New purchasing manager"),
    (8, "Elvekanten Freight", "Logistics", 3600000, 41, 210, "Fewer logins this month"),
    (9, "Kvernhuset Mills", "Manufacturing", 1750000, 36, 95, "Stable, with one open complaint"),
    (10, "Morild Retail Group", "Retail", 4700000, 33, 240, "Stable order volume"),
    (11, "Sjosiden Restaurants", "Hospitality", 1400000, 28, 180, "Stable order volume"),
    (12, "Stormkast Shipping", "Logistics", 6200000, 24, 300, "Growing order volume"),
    (13, "Vinterlys Home", "Retail", 1150000, 19, 130, "Renewed early last year"),
    (14, "Granhogda Timber", "Manufacturing", 2050000, 15, 270, "Growing order volume"),
    (15, "Polarsirkel Couriers", "Logistics", 1650000, 12, 160, "Added a second contract"),
    (16, "Tunet Guesthouses", "Hospitality", 720000, 9, 330, "Long-term customer"),
]


def text(value):
    return "'" + value.replace("'", "''") + "'"


def months_back(count):
    today = date.today().replace(day=1)
    index = today.year * 12 + today.month - 1
    return [date((i // 12), i % 12 + 1, 1) for i in range(index - count + 1, index + 1)]


def revenue_rows():
    rng = random.Random(42)
    months = months_back(12)
    rows = []
    for account_id, _, _, value, risk, _, _ in CUSTOMERS:
        monthly = value / 12
        # Higher risk means a falling trend over the year.
        change = (40 - risk) / 100 / 11
        for i, month in enumerate(months):
            noise = rng.uniform(0.94, 1.06)
            amount = int(monthly * (1 + change * (i - 5.5)) * noise)
            rows.append(f"({account_id}, DATE'{month}', {amount})")
    return rows


def support_rows():
    rng = random.Random(7)
    rows = []
    for account_id, _, _, _, risk, _, _ in CUSTOMERS:
        open_tickets = risk // 12 + rng.randint(0, 2)
        tickets_90_days = open_tickets * 2 + rng.randint(1, 5)
        rows.append(f"({account_id}, {open_tickets}, {tickets_90_days})")
    return rows


def create_tables(wh):
    sql(f"""
    CREATE TABLE IF NOT EXISTS {ACCOUNTS} (
      account_id INT NOT NULL,
      account_name STRING NOT NULL,
      segment STRING NOT NULL,
      annual_value_nok BIGINT NOT NULL,
      risk_score INT NOT NULL,
      renewal_date DATE NOT NULL,
      risk_reason STRING NOT NULL,
      updated_at TIMESTAMP NOT NULL
    )
    COMMENT 'Synthetic demo data: customers scored by risk of leaving.'
    TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """, wh)

    sql(f"""
    CREATE TABLE IF NOT EXISTS {REVENUE} (
      account_id INT NOT NULL,
      month DATE NOT NULL,
      revenue_nok BIGINT NOT NULL
    )
    COMMENT 'Synthetic demo data: monthly revenue per customer.'
    TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """, wh)

    sql(f"""
    CREATE TABLE IF NOT EXISTS {SUPPORT} (
      account_id INT NOT NULL,
      open_tickets INT NOT NULL,
      tickets_90_days INT NOT NULL
    )
    COMMENT 'Synthetic demo data: support tickets per customer.'
    TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """, wh)


def write_rows(wh, restore=False):
    """Insert the rows that are missing. With restore=True, also put changed rows back and remove extra rows."""
    accounts = ", ".join(
        f"({c[0]}, {text(c[1])}, {text(c[2])}, {c[3]}, {c[4]}, date_add(current_date(), {c[5]}), {text(c[6])})"
        for c in CUSTOMERS
    )
    account_columns = ["account_name", "segment", "annual_value_nok", "risk_score", "renewal_date", "risk_reason"]
    merges = [
        (ACCOUNTS, accounts, ["account_id"], account_columns,
         "col1 AS account_id, col2 AS account_name, col3 AS segment, col4 AS annual_value_nok, "
         "col5 AS risk_score, col6 AS renewal_date, col7 AS risk_reason"),
        (REVENUE, ", ".join(revenue_rows()), ["account_id", "month"], ["revenue_nok"],
         "col1 AS account_id, col2 AS month, col3 AS revenue_nok"),
        (SUPPORT, ", ".join(support_rows()), ["account_id"], ["open_tickets", "tickets_90_days"],
         "col1 AS account_id, col2 AS open_tickets, col3 AS tickets_90_days"),
    ]
    for table, values, keys, columns, select in merges:
        stamp = table == ACCOUNTS
        on = " AND ".join(f"t.{k} = s.{k}" for k in keys)
        insert_columns = keys + columns + (["updated_at"] if stamp else [])
        insert_values = [f"s.{c}" for c in keys + columns] + (["current_timestamp()"] if stamp else [])
        clauses = []
        if restore:
            changed = " OR ".join(f"t.{c} <> s.{c}" for c in columns)
            updates = [f"{c} = s.{c}" for c in columns] + (["updated_at = current_timestamp()"] if stamp else [])
            clauses.append(f"WHEN MATCHED AND ({changed}) THEN UPDATE SET {', '.join(updates)}")
        clauses.append(
            f"WHEN NOT MATCHED THEN INSERT ({', '.join(insert_columns)}) VALUES ({', '.join(insert_values)})"
        )
        if restore:
            clauses.append("WHEN NOT MATCHED BY SOURCE THEN DELETE")
        newline = "\n"
        sql(f"""
        MERGE INTO {table} AS t
        USING (SELECT {select} FROM VALUES {values}) AS s
        ON {on}
        {newline.join(clauses)}
        """, wh)


def row_counts(wh):
    for table in (ACCOUNTS, REVENUE, SUPPORT):
        count = sql(f"SELECT count(*) FROM {table}", wh)["result"]["data_array"][0][0]
        print(f"{table}: {count} rows")

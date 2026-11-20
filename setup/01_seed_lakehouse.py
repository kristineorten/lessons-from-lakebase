"""Create the schema and the synthetic source tables. Safe to run again."""
from common import CATALOG, SCHEMA, cli, warehouse_id
from demo_data import create_tables, row_counts, write_rows

wh = warehouse_id()
cli("schemas", "create", SCHEMA, CATALOG, "--comment", "Synthetic demo data.", check=False)
create_tables(wh)
write_rows(wh)
row_counts(wh)

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

LOAD_ORDER = ["dim_date", "dim_supplier", "dim_product", "dim_customer", "fact_sales", "fact_inventory_snapshot", "fact_returns"]   


def build_db(src="data/raw", db="db/analytics.db", schema="db/schema.sql"):
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    Path(db).unlink(missing_ok=True)
    with closing(sqlite3.connect(db)) as con:
        con.executescript(Path(schema).read_text())      # includes PRAGMA foreign_keys = ON
        for t in LOAD_ORDER:
            df = pd.read_csv(Path(src) / f"{t}.csv")
            df.to_sql(t, con, if_exists="append", index=False, chunksize=50_000)
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"{t:28s}{n:>10,}")
        bad = con.execute("PRAGMA foreign_key_check").fetchall()
        assert not bad, f"Foreign key violations: {bad[:5]}"
        con.commit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw")
    ap.add_argument("--db", default="db/analytics.db")
    a = ap.parse_args()
    build_db(a.src, a.db)
import sqlite3
from contextlib import closing

import streamlit as st

from analytics import queries
from app import config


def ensure_db():
    """On a fresh deploy there is no DB file, so build it from the committed sample CSVs."""
    if not config.DB_PATH.exists():
        from etl.load import build_db
        build_db(src=str(config.SAMPLE_DIR), db=str(config.DB_PATH))


# `stamp` (the DB file's modified time) is part of the cache key, so the cache refreshes
# automatically when the database changes. A parameter starting with "_" would NOT be hashed.
@st.cache_data(ttl=3600, show_spinner="Loading sales data…")
def load_sales(stamp: float):
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        return queries.sales_enriched(con)


@st.cache_data(ttl=3600, show_spinner="Loading inventory…")
def load_inventory(stamp: float):
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        return queries.inventory_all(con)
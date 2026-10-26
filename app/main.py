import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # so `import analytics` works anywhere

import streamlit as st

from app import config, data
from app.components.filters import role_selector, sidebar_filters

st.set_page_config(page_title=config.APP_TITLE, page_icon="📊", layout="wide")

data.ensure_db()
stamp = config.DB_PATH.stat().st_mtime
sales = data.load_sales(stamp)
inventory = data.load_inventory(stamp)

role = role_selector()
current, prior, meta = sidebar_filters(sales)
st.session_state.update(
    role=role,
    sales_all=sales,
    sales_f=current,
    sales_prior=prior,
    inventory=inventory,
    filters=meta,
)

PAGE_DEFS = {
    "overview": ("pages/overview.py", "Overview", "📈"),
    "explorer": ("pages/sales_explorer.py", "Sales Explorer", "🔎"),
    "inventory": ("pages/inventory_health.py", "Inventory Health", "📦"),
    "quality": ("pages/data_quality.py", "Data & Quality", "✅"),
    "report": ("pages/report.py", "Report", "📄"),
}

app_dir = Path(__file__).resolve().parent
wanted = [PAGE_DEFS[k] for k in config.ROLE_PAGES[role]]
pages = [
    st.Page(path, title=title, icon=icon, default=(path == "pages/overview.py"))
    for path, title, icon in wanted
    if (app_dir / path).exists()
]
missing = [path for path, _, _ in wanted if not (app_dir / path).exists()]

if missing:
    st.sidebar.caption(
        "Not built yet: " + ", ".join(missing)
    )  # dev aid; delete when all pages exist
if not pages:
    st.error("No pages found in app/pages/. Create overview.py first.")
    st.stop()

st.navigation(pages).run()

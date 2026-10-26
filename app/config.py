import os
from pathlib import Path

APP_TITLE = "Sales & Inventory Analytics"
DB_PATH = Path(os.getenv("DB_PATH", "db/analytics.db"))
SAMPLE_DIR = Path("data/sample")
ROLES = ["Executive", "Sales", "Ops", "Analyst"]

ROLE_PAGES = {
    "Executive": ["overview", "report"],
    "Sales": ["overview", "explorer", "report"],
    "Ops": ["overview", "inventory", "report"],
    "Analyst": ["overview", "explorer", "inventory", "quality", "report"],
}
ROLE_KPIS = {
    "Executive": ["net_revenue", "gross_margin_pct", "fill_rate", "return_rate"],
    "Sales": ["net_revenue", "units_sold", "aov", "return_rate"],
    "Ops": ["fill_rate", "return_rate", "units_sold"],
    "Analyst": [
        "net_revenue",
        "gross_margin_pct",
        "aov",
        "units_sold",
        "fill_rate",
        "return_rate",
    ],
}

"""05: Buat view SQL (DuckDB) dan ekspor hasilnya ke CSV (Q1, Q3, Q4, Q5, Q6, Q8, komponen scorecard).

Hasil dibulatkan 10 desimal agar jalan ulang menghasilkan CSV identik.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb
import pandas as pd
import common as C

con = duckdb.connect(str(C.DB_PATH))
sql = (C.SQL_DIR / "views.sql").read_text(encoding="utf-8")
sql = sql.replace("{LOT_MIN_UNITS}", str(C.LOT_MIN_UNITS)).replace("{ROLL_WEEKS_MINUS1}", str(C.ROLL_WEEKS - 1)) \
         .replace("{ROLL_WEEKS}", str(C.ROLL_WEEKS))
for stmt in [s.strip() for s in sql.split(";") if s.strip() and not all(l.startswith("--") for l in s.strip().splitlines())]:
    con.execute(stmt)

INT_COLS = {"units", "ng", "lots", "units_4w", "ng_4w", "lots_eval", "prior_months", "week_no", "input_qty", "ng_material_qty"}
EXPORT = {
    "ng_supplier.csv": "SELECT * FROM v_ng_supplier ORDER BY supplier_code",
    "ng_supplier_material.csv": "SELECT * FROM v_ng_supplier_material ORDER BY supplier_code, material_code",
    "ng_month.csv": "SELECT * FROM v_ng_month ORDER BY month, rank_ng, supplier_code",
    "rolling_weekly.csv": "SELECT * FROM v_weekly ORDER BY supplier_code, week_start",
    "lot_level.csv": "SELECT * FROM v_lot ORDER BY lot_code",
    "lot_cv.csv": "SELECT * FROM v_lot_cv ORDER BY supplier_code",
    "score_components.csv": "SELECT * FROM v_score_components ORDER BY month, supplier_code",
    "cross_model.csv": "SELECT * FROM v_cross_model ORDER BY supplier_code, model_code",
    "cross_station.csv": "SELECT * FROM v_cross_station ORDER BY supplier_code, station_code",
    "usage_detail.csv": "SELECT date, month, week_start, lot_code, supplier_code, material_code, station_code, model_code, "
                        "input_qty, ng_material_qty FROM v_usage ORDER BY date, lot_code, station_code, model_code, input_qty, ng_material_qty",
}
for name, q in EXPORT.items():
    df = con.execute(q).df()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            if c in INT_COLS:
                df[c] = df[c].round().astype("Int64")
            else:
                df[c] = df[c].round(10)
    df.to_csv(C.RES2 / name, index=False)
    print(f"{name}: {len(df)} baris")
con.close()

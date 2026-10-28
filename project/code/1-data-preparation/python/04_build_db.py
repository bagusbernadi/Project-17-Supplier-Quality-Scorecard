"""04: Muat data bersih ke DuckDB (supplier.duckdb) dan jalankan aturan pengecekan database.

Tabel: dim_supplier, material_lot, lot_usage. scorecard_monthly ditambahkan oleh 09_scorecard.py.
Hasil: supplier.duckdb (tidak di-commit), results/1-data-preparation/db_checks.csv dan db_tables.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb
import pandas as pd
from common import CLEAN, DB_PATH, RES1

if DB_PATH.exists():
    DB_PATH.unlink()
con = duckdb.connect(str(DB_PATH))
con.execute(f"""
CREATE TABLE dim_supplier AS SELECT supplier_code, material_code, CAST(active_from AS DATE) AS active_from
  FROM read_csv('{CLEAN / "dim_supplier_clean.csv"}', header=true);
CREATE TABLE material_lot AS SELECT lot_code, supplier_code, material_code, CAST(receive_date AS DATE) AS receive_date,
  CAST(lot_qty AS INTEGER) AS lot_qty, incoming_result FROM read_csv('{CLEAN / "material_lot_clean.csv"}', header=true);
CREATE TABLE lot_usage AS SELECT CAST(date AS DATE) AS date, lot_code, station_code, model_code,
  CAST(input_qty AS INTEGER) AS input_qty, CAST(ng_material_qty AS INTEGER) AS ng_material_qty
  FROM read_csv('{CLEAN / "lot_usage_clean.csv"}', header=true);
""")
checks = [
    ("NG tidak boleh melebihi input", "SELECT count(*) FROM lot_usage WHERE ng_material_qty > input_qty"),
    ("input harus positif", "SELECT count(*) FROM lot_usage WHERE input_qty <= 0"),
    ("setiap pemakaian punya lot", "SELECT count(*) FROM lot_usage u LEFT JOIN material_lot l USING (lot_code) WHERE l.lot_code IS NULL"),
    ("kode lot unik", "SELECT count(*) - count(DISTINCT lot_code) FROM material_lot"),
    ("setiap lot punya supplier dan material", "SELECT count(*) FROM material_lot WHERE supplier_code IS NULL OR material_code IS NULL"),
    ("pasangan supplier-material ada di dim_supplier", "SELECT count(*) FROM material_lot l LEFT JOIN dim_supplier d USING (supplier_code, material_code) WHERE d.supplier_code IS NULL"),
    ("pemakaian tidak sebelum tanggal terima", "SELECT count(*) FROM lot_usage u JOIN material_lot l USING (lot_code) WHERE u.date < l.receive_date"),
]
rows = []
for name, q in checks:
    n = int(con.execute(q).fetchone()[0])
    rows.append(dict(pengecekan=name, pelanggaran=n, hasil="lulus" if n == 0 else "gagal"))
pd.DataFrame(rows).to_csv(RES1 / "db_checks.csv", index=False)
tabs = [dict(tabel=t, baris=int(con.execute(f"SELECT count(*) FROM {t}").fetchone()[0])) for t in ("dim_supplier", "material_lot", "lot_usage")]
pd.DataFrame(tabs).to_csv(RES1 / "db_tables.csv", index=False)
con.close()
bad = [r for r in rows if r["hasil"] != "lulus"]
print("tabel:", {t["tabel"]: t["baris"] for t in tabs}, "| pengecekan lulus:", len(rows) - len(bad), "dari", len(rows))
assert not bad, bad

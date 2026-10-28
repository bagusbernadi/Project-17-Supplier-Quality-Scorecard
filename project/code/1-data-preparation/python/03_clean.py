"""03: Audit kualitas data dan cleaning (Q13). Menautkan setiap pemakaian ke lot dan supplier.

Aturan (rancangan: lot tanpa supplier, NG tanpa lot, duplikat; asumsi tambahan ditandai di docs/cleaning_decisions.md):
  1. lot tanpa supplier atau material      2. pemakaian tanpa lot di tabel lot
  3. lot ganda (kode sama)                 4. baris pemakaian ganda
  5. ng_material_qty > input_qty          6. input_qty <= 0
  7. pemakaian sebelum tanggal terima lot  8. pasangan supplier-material tidak ada di dim_supplier
Baris pemakaian yang melanggar aturan 2 sampai 8 tidak masuk analisis (valid = 0) dan dicatat di cleaning_log.csv.
Hasil: data/clean/*.csv, results/1-data-preparation/data_quality.csv dan cleaning_log.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from common import ANON, CLEAN, RES1

lot = pd.read_csv(ANON / "material_lot.csv", dtype=str, keep_default_na=False)
use = pd.read_csv(ANON / "lot_usage.csv", dtype=str, keep_default_na=False)
dim = pd.read_csv(ANON / "dim_supplier.csv", dtype=str, keep_default_na=False)
n_lot_raw, n_use_raw = len(lot), len(use)
for c in ("lot_qty",):
    lot[c] = pd.to_numeric(lot[c], errors="coerce")
for c in ("input_qty", "ng_material_qty"):
    use[c] = pd.to_numeric(use[c], errors="coerce")
lot["receive_date"] = pd.to_datetime(lot["receive_date"])
use["date"] = pd.to_datetime(use["date"])

issues = {}                                           # kategori -> jumlah
log = []                                              # baris bermasalah

# 1 dan 3: tabel lot
no_sup = (lot.supplier_code == "") | (lot.material_code == "")
issues["lot tanpa supplier atau material"] = int(no_sup.sum())
dup_lot = lot.duplicated("lot_code", keep="first")
issues["lot ganda"] = int(dup_lot.sum())
for i in lot.index[no_sup | dup_lot]:
    log.append(("material_lot", lot.at[i, "lot_code"], "lot tanpa supplier atau ganda", "dibuang"))
lot_ok = lot[~(no_sup | dup_lot)].copy()
pairs = set(zip(dim.supplier_code, dim.material_code))
bad_pair_lot = ~pd.Series([(s, m) in pairs for s, m in zip(lot_ok.supplier_code, lot_ok.material_code)], index=lot_ok.index)
issues["pasangan supplier-material tidak ada di dim_supplier"] = int(bad_pair_lot.sum())
for i in lot_ok.index[bad_pair_lot]:
    log.append(("material_lot", lot_ok.at[i, "lot_code"], "pasangan supplier-material tidak terdaftar", "dibuang"))
lot_ok = lot_ok[~bad_pair_lot]

# tabel pemakaian
u = use.copy()
u["alasan"] = "valid"
dup_use = u.duplicated(keep="first")
issues["baris pemakaian ganda"] = int(dup_use.sum())
no_lot = ~u.lot_code.isin(lot_ok.lot_code)
issues["pemakaian tanpa lot"] = int(no_lot.sum())
ng_gt = u.ng_material_qty > u.input_qty
issues["NG lebih besar dari input"] = int(ng_gt.sum())
nonpos = ~(u.input_qty > 0)
issues["input tidak positif"] = int(nonpos.sum())
m = u.merge(lot_ok[["lot_code", "receive_date"]], on="lot_code", how="left")
early = (m["date"] < m["receive_date"]).fillna(False).to_numpy()
issues["pemakaian sebelum lot diterima"] = int(early.sum())
for name, mask in (("baris pemakaian ganda", dup_use), ("pemakaian tanpa lot", no_lot), ("NG lebih besar dari input", ng_gt),
                   ("input tidak positif", nonpos), ("pemakaian sebelum lot diterima", pd.Series(early, index=u.index))):
    sel = u.alasan == "valid"
    u.loc[mask & sel, "alasan"] = name
u["valid"] = (u.alasan == "valid").astype(int)
for i in u.index[u.valid == 0]:
    log.append(("lot_usage", u.at[i, "lot_code"], u.at[i, "alasan"], "dibuang dari analisis"))

use_ok = u[u.valid == 1].drop(columns=["alasan", "valid"])
lot_ok.to_csv(CLEAN / "material_lot_clean.csv", index=False, date_format="%Y-%m-%d")
use_ok.to_csv(CLEAN / "lot_usage_clean.csv", index=False, date_format="%Y-%m-%d")
dim.to_csv(CLEAN / "dim_supplier_clean.csv", index=False)

# info (bukan pelanggaran): lot yang dinyatakan Reject saat penerimaan tetapi dipakai
rej = lot_ok[lot_ok.incoming_result == "Reject"].lot_code
n_rej_used = int(use_ok.lot_code.isin(rej).sum())
n_lot_unused = int((~lot_ok.lot_code.isin(use_ok.lot_code)).sum())

dq = [("baris lot (mentah)", n_lot_raw, n_lot_raw, "dasar"), ("baris pemakaian (mentah)", n_use_raw, n_use_raw, "dasar")]
for k, v in issues.items():
    base = n_lot_raw if k.startswith(("lot", "pasangan")) else n_use_raw
    dq.append((k, v, base, "dibuang" if v else "tidak ada"))
dq += [("baris pemakaian valid", len(use_ok), n_use_raw, "dipakai"),
       ("lot dengan hasil Reject saat penerimaan yang tetap dipakai (info)", n_rej_used, len(use_ok), "dipakai, ditandai di scorecard"),
       ("lot tanpa pemakaian (info)", n_lot_unused, n_lot_raw, "dipertahankan di tabel lot")]
pd.DataFrame([dict(kategori=k, jumlah=v, dasar=b, proporsi=round(v / b, 6) if b else 0.0, keputusan=d) for k, v, b, d in dq]
             ).to_csv(RES1 / "data_quality.csv", index=False)
pd.DataFrame(log, columns=["tabel", "kunci", "alasan", "keputusan"]).to_csv(RES1 / "cleaning_log.csv", index=False)
print(f"lot {n_lot_raw}->{len(lot_ok)}; pemakaian {n_use_raw}->{len(use_ok)}; pelanggaran: {sum(issues.values())}")

"""Project 17 (langkah 2 dari 2): anonymization data simulasi lot -> data/anon/. Seed tetap.

Supplier, material, stasiun, model, dan kode lot diganti kode acak; jumlah unit diskala. Tabel pemetaan dan
faktor skala disimpan di data/private/ (tidak pernah di-commit). Hasil (data/anon/): dim_supplier.csv,
material_lot.csv, lot_usage.csv, ground_truth.json (memakai kode anonim).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRIV, ANON = ROOT / "data" / "private", ROOT / "data" / "anon"
RAW = PRIV / "raw"
SEED = 17260999                        # seed terpisah untuk pemetaan kode
SCALE = 0.42                           # faktor skala jumlah unit (rahasia, ikut private)

rng = np.random.default_rng(SEED)
rc = pd.read_csv(RAW / "receipts.csv", parse_dates=["receive_date"])
us = pd.read_csv(RAW / "usage.csv", parse_dates=["date"])


def code_map(values, prefix, letters=False):
    vals = sorted(set(values))
    order = rng.permutation(len(vals))
    tags = [chr(65 + i) if letters else str(i + 1) for i in range(len(vals))]
    return {v: f"{prefix}{tags[int(o)]}" for v, o in zip(vals, order)}


sup = code_map(rc["supplier_name"], "SUP-", letters=True)
mat = code_map(rc["material_name"], "MAT-")
sta = code_map(us["station_name"], "ST-", letters=True)
mod = code_map(us["model_name"], "M-")
lots = {l: f"L-{int(x):04X}" for l, x in zip(sorted(set(rc["lot_code"])), rng.choice(65536, len(set(rc["lot_code"])), replace=False))}

lot = pd.DataFrame({"lot_code": rc["lot_code"].map(lots), "supplier_code": rc["supplier_name"].map(sup),
                    "material_code": rc["material_name"].map(mat), "receive_date": rc["receive_date"].dt.date,
                    "lot_qty": (rc["lot_qty"] * SCALE).round().astype(int), "incoming_result": rc["incoming_result"]})
use = pd.DataFrame({"date": us["date"].dt.date, "lot_code": us["lot_code"].map(lots), "station_code": us["station_name"].map(sta),
                    "model_code": us["model_name"].map(mod), "input_qty": (us["input_qty"] * SCALE).round().astype(int),
                    "ng_material_qty": (us["ng_material_qty"] * SCALE).round().astype(int)})
dim = (rc.assign(supplier_code=rc["supplier_name"].map(sup), material_code=rc["material_name"].map(mat))
         .groupby(["supplier_code", "material_code"], as_index=False)["receive_date"].min()
         .rename(columns={"receive_date": "active_from"}).sort_values(["supplier_code", "material_code"]))
dim["active_from"] = dim["active_from"].dt.date

ANON.mkdir(parents=True, exist_ok=True)
lot.sort_values("lot_code").to_csv(ANON / "material_lot.csv", index=False)
use.to_csv(ANON / "lot_usage.csv", index=False)
dim.to_csv(ANON / "dim_supplier.csv", index=False)
(PRIV / "mapping.json").write_text(json.dumps({"supplier": sup, "material": mat, "station": sta, "model": mod,
                                              "scale": SCALE}, indent=2, ensure_ascii=False), encoding="utf-8")
gt_raw = json.loads((RAW / "ground_truth_raw.json").read_text(encoding="utf-8"))
txt = json.dumps(gt_raw, ensure_ascii=False)
for table in (sup, mod):
    for k, v in table.items():
        txt = txt.replace(k, v)
(ANON / "ground_truth.json").write_text(json.dumps(json.loads(txt), indent=2, ensure_ascii=False), encoding="utf-8")

# cek: tidak ada nama asli tersisa di berkas anonim
leak = [n for n in list(sup) + list(mat) + list(sta) + list(mod) if any(n in p.read_text(encoding="utf-8") for p in ANON.glob("*"))]
assert not leak, f"nama asli tersisa: {leak}"
print(f"anon: {len(lot)} lot, {len(use)} baris pemakaian, {len(dim)} pasangan supplier-material; cek kebocoran nama: lolos")

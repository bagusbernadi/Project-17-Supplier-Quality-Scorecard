"""Project 17 (langkah 1 dari 2): data penerimaan lot dan NG material SIMULASI dengan identitas bernama. Seed tetap.

Data ini 100% karangan (nama supplier, material, model, stasiun, kode lot fiktif), tetapi dibuat berbentuk
seperti data kerja supaya langkah anonymization (anonymize.py) bisa dilatih dan diuji.
Hasil (data/private/raw/, tidak di-commit): suppliers.csv, receipts.csv, usage.csv, ground_truth_raw.json.
Jalankan: python scripts/generate_raw.py && python scripts/anonymize.py   (versi data: v1)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "private" / "raw"
SEED = 17260302
DATA_VERSION = "v1"
START, N_DAYS = "2026-03-02", 130                 # Mar - Agu 2026, hari kerja

SUPPLIERS = {                                      # nama fiktif: (bobot volume, pengali NG, material yang dipasok)
    "PT Sinar Logam Perkasa": (0.30, 1.00, ["Kabel UL1007 AWG22"]),
    "CV Karya Konektor Mandiri": (0.27, 0.95, ["Konektor 4-pin"]),
    "PT Mitra Plastik Nusantara": (0.20, 1.05, ["Housing plastik", "Konektor 4-pin"]),
    "PT Cahaya Kabel Utama": (0.20, 2.30, ["Kabel UL1007 AWG22", "Housing plastik"]),   # terburuk
    "UD Tiga Saudara Teknik": (0.03, 1.10, ["Konektor 4-pin"]),                    # volume kecil
}
WORSENING = "PT Mitra Plastik Nusantara"           # memburuk 2 bulan terakhir
WORSEN_FROM_DAY, WORSEN_FACTOR = 90, 2.2
BAD_LOT_SHARE, BAD_LOT_FACTOR = 0.08, 6.0           # sedikit lot menyumbang banyak NG
MODELS = ["Harness X100", "Harness X200", "Harness X300"]
MODEL_FACTOR = [0.8, 1.0, 1.6]
STATIONS = ["Cutting", "Crimping", "Assembly", "Soldering", "Final Test"]
BASE_RATE = 0.008
N_LOTS = 1200

rng = np.random.default_rng(SEED)
days = pd.bdate_range(START, periods=N_DAYS)
names = list(SUPPLIERS)
w = np.array([SUPPLIERS[n][0] for n in names])
w = w / w.sum()

receipts, usage = [], []
for k in range(N_LOTS):
    sup = names[int(rng.choice(len(names), p=w))]
    mat = SUPPLIERS[sup][2][int(rng.integers(0, len(SUPPLIERS[sup][2])))]
    d = int(rng.integers(0, N_DAYS - 6))
    lot = f"{days[d].strftime('%y%m')}-{sup.split()[1][:2].upper()}-{k + 1:04d}"
    qty = int(rng.integers(8, 61)) * 100
    bad = bool(rng.random() < BAD_LOT_SHARE)
    inc = "Pass" if rng.random() < 0.94 else ("Conditional" if rng.random() < 0.65 else "Reject")
    receipts.append([lot, sup, mat, days[d].date(), qty, inc])
    # pemakaian: 1-3 hari, 1-2 stasiun/model per hari. Supplier terburuk lebih sering dipakai di model terberat (X300)
    remaining = qty
    for u in range(int(rng.integers(1, 4))):
        ud = min(d + 1 + u, N_DAYS - 1)
        for _ in range(int(rng.integers(1, 3))):
            if remaining <= 0:
                break
            inp = int(min(remaining, rng.integers(150, 600)))
            remaining -= inp
            heavy = sup == "PT Cahaya Kabel Utama" and rng.random() < 0.6
            mi = 2 if heavy else int(rng.integers(0, 3))
            st = STATIONS[int(rng.integers(0, len(STATIONS)))]
            p = BASE_RATE * SUPPLIERS[sup][1] * MODEL_FACTOR[mi]
            if sup == WORSENING and ud >= WORSEN_FROM_DAY:
                p *= WORSEN_FACTOR
            if bad:
                p *= BAD_LOT_FACTOR
            ng = int(rng.binomial(inp, min(p, 0.4)))
            usage.append([days[ud].date(), lot, st, MODELS[mi], inp, ng])

RAW.mkdir(parents=True, exist_ok=True)
pd.DataFrame(receipts, columns=["lot_code", "supplier_name", "material_name", "receive_date", "lot_qty", "incoming_result"]
             ).to_csv(RAW / "receipts.csv", index=False)
pd.DataFrame(usage, columns=["date", "lot_code", "station_name", "model_name", "input_qty", "ng_material_qty"]
             ).to_csv(RAW / "usage.csv", index=False)
pd.DataFrame([(n, SUPPLIERS[n][2][0]) for n in names], columns=["supplier_name", "first_material"]).to_csv(RAW / "suppliers.csv", index=False)
gt = {"seed": SEED, "version": DATA_VERSION,
      "facts": [{"id": 1, "fact": "Supplier dengan NG rate tertinggi", "supplier_name": "PT Cahaya Kabel Utama", "factor": 2.30},
                {"id": 2, "fact": "Sebagian kecil lot menyumbang banyak NG", "bad_lot_share": BAD_LOT_SHARE, "factor": BAD_LOT_FACTOR},
                {"id": 3, "fact": "Supplier memburuk sejak hari ke-90 (+-2 bulan terakhir)", "supplier_name": WORSENING,
                 "from": str(days[WORSEN_FROM_DAY].date()), "factor": WORSEN_FACTOR},
                {"id": 4, "fact": "Perbedaan sebagian karena model: supplier terburuk 60% dipakai di Harness X300 (NG rate model 1,6x)"},
                {"id": 5, "fact": "Supplier volume kecil belum bisa diberi status", "supplier_name": "UD Tiga Saudara Teknik"}]}
(RAW / "ground_truth_raw.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"{len(receipts)} lot, {len(usage)} baris pemakaian -> {RAW}")

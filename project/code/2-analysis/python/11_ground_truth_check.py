"""11: Uji pemulihan fakta yang ditanam (ground truth). Skrip ini satu-satunya yang membaca data/anon/ground_truth.json.

Kriteria ditetapkan sebelum hasil dilihat: lihat kolom kriteria. Hasil: results/2-analysis/ground_truth_check.csv
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import common as CM

R = CM.RES2
gt = json.loads((CM.ANON / "ground_truth.json").read_text(encoding="utf-8"))
F = {f["id"]: f for f in gt["facts"]}
sup = pd.read_csv(R / "ng_supplier.csv").set_index("supplier_code")
hy = pd.read_csv(R / "hypotheses.csv").set_index("id")
q1top = pd.read_csv(R / "q1_top_per_material.csv")
cm = pd.read_csv(R / "cross_model.csv")
sc = pd.read_csv(R / "scorecard_monthly.csv")
wk = pd.read_csv(R / "rolling_weekly.csv", parse_dates=["week_start"])
conc = pd.read_csv(R / "concentration_lots.csv")
q4 = pd.read_csv(R / "q4_lot_variation.csv")
lots = pd.read_csv(R / "lot_level.csv")
rows = []

# Fakta 1: supplier terburuk
s1 = F[1]["supplier_name"]
top = sup.ng_rate.idxmax()
others = sup.drop(s1)
ratio = float(sup.loc[s1, "ng_rate"] / (others.ng.sum() / others.units.sum()))
sig = int((q1top[q1top.supplier_tertinggi == s1].shape[0]) >= 1 and hy.loc["H1", "verdict"] == "Terbukti")
ok = top == s1 and sig
rows.append(dict(id=1, fakta=F[1]["fact"], ditanam=f"{s1}, pengali NG {F[1]['factor']}", terdeteksi=f"{top} tertinggi; NG rate {ratio:.2f} kali supplier lain; tertinggi signifikan pada {int((q1top.supplier_tertinggi == s1).sum())} material",
                 kriteria="supplier tertinggi sama dan signifikan pada sedikitnya satu material (H1)", hasil="Sesuai" if ok else "Tidak sesuai"))

# Fakta 2: sedikit lot menyumbang banyak NG
share = float(conc.persen_ng_dari_lot_teratas.mean()); base = float(conc.pembanding_lot_seragam.mean())
bad = float(F[2]["bad_lot_share"]); fac = float(F[2]["factor"])
expect_share = bad * fac / (bad * fac + (1 - bad))
ok_over = (conc.persen_ng_dari_lot_teratas > conc.pembanding_lot_seragam + 0.05).all()
disp_ok = bool((q4.dispersi_berlebih > 1.5).all())
rows.append(dict(id=2, fakta=F[2]["fact"], ditanam=f"{bad:.0%} lot dengan NG {fac:g} kali; porsi NG dari lot tersebut sekitar {expect_share:.0%}",
                 terdeteksi=f"10% lot teratas menyumbang {share:.0%} NG (pembanding lot seragam {base:.0%}); dispersi berlebih di semua supplier: {'ya' if disp_ok else 'tidak'}",
                 kriteria="10% lot teratas melebihi pembanding seragam sedikitnya 5 poin persentase di semua supplier, dispersi berlebih > 1,5; tidak harus > 50%",
                 hasil="Sesuai" if (ok_over and disp_ok) else "Sebagian"))

# Fakta 3: supplier memburuk, tanggal
s3 = F[3]["supplier_name"]
d = wk[wk.supplier_code == s3].sort_values("week_start")
base_part = d.iloc[:12]
pb = base_part.ng.sum() / base_part.units.sum()
d = d.assign(ucl=pb + 3 * np.sqrt(pb * (1 - pb) / d.units_4w))
hit = d[(d.week_start > base_part.week_start.max()) & (d.rolling_ng_rate > d.ucl)]
det = hit.week_start.iloc[0] if len(hit) else None
true_d = pd.Timestamp(F[3]["from"])
gap_w = abs((det - true_d).days) / 7 if det is not None else np.nan
q6 = pd.read_csv(R / "q6_worsening.csv").set_index("supplier_code")
only = list(q6[q6.memburuk == 1].index) == [s3]
ok3 = only and det is not None and gap_w <= 2
rows.append(dict(id=3, fakta=F[3]["fact"], ditanam=f"{s3} sejak {F[3]['from']}, pengali {F[3]['factor']}",
                 terdeteksi=f"memburuk terdeteksi hanya pada {', '.join(q6[q6.memburuk == 1].index)}; rolling 4 minggu melewati batas p-chart pada minggu {det.date() if det is not None else '-'} (selisih {gap_w:.1f} minggu)",
                 kriteria="hanya supplier itu yang memburuk (H3) dan titik awal terdeteksi dalam 2 minggu",
                 hasil="Sesuai" if ok3 else "Sebagian"))

# Fakta 4: model
s_worst = F[1]["supplier_name"]
w = cm[cm.supplier_code == s_worst].set_index("model_code")
share_m2 = float(w.loc["M-2", "units"] / w.units.sum())
allm = cm.groupby("model_code").agg(units=("units", "sum"), ng=("ng", "sum"))
allm["r"] = allm.ng / allm.units
# NG rate M-2 dibanding M-1 dan M-3 tanpa supplier terburuk (hindari pencampuran)
nm_ = cm[cm.supplier_code != s_worst].groupby("model_code").agg(units=("units", "sum"), ng=("ng", "sum"))
nm_["r"] = nm_.ng / nm_.units
ratio_m = float(nm_.loc["M-2", "r"] / nm_.drop("M-2").r.mean())
ok4 = abs(share_m2 - 0.60) <= 0.10 and 1.3 <= ratio_m <= 2.0 and hy.loc["H4", "verdict"] == "Terbukti"
rows.append(dict(id=4, fakta=F[4]["fact"], ditanam="60% pemakaian supplier terburuk di M-2; NG rate M-2 1,6 kali",
                 terdeteksi=f"{share_m2:.0%} pemakaian {s_worst} di M-2; NG rate M-2 {ratio_m:.2f} kali model lain (tanpa {s_worst}); model dan stasiun menjelaskan sebagian selisih (H4: {hy.loc['H4', 'verdict']})",
                 kriteria="porsi M-2 pada 60% plus minus 10 poin, rasio model 1,3 sampai 2,0, H4 terbukti",
                 catatan="Pemakaian di M-2 yang ditanam efektif sekitar 73% (60% khusus M-2 ditambah sepertiga dari sisanya acak), jadi batas 60% plus minus 10 poin ketat.",
                 hasil="Sesuai" if ok4 else "Sebagian"))

# Fakta 5: supplier volume kecil
s5 = F[5]["supplier_name"]
r5 = sc[sc.supplier_code == s5]
frac = float((r5.status == "belum dinilai").mean())
rows.append(dict(id=5, fakta=F[5]["fact"], ditanam=f"{s5} bervolume kecil (3% bobot)",
                 terdeteksi=f"{s5} belum dinilai pada {int((r5.status == 'belum dinilai').sum())} dari {len(r5)} bulan; H5: {hy.loc['H5', 'verdict']}",
                 kriteria="belum dinilai pada sedikitnya separuh bulan",
                 hasil="Sesuai" if frac >= 0.5 else "Sebagian"))
out = pd.DataFrame(rows)
out.to_csv(R / "ground_truth_check.csv", index=False)
print(out[["id", "terdeteksi", "hasil"]].to_string(index=False))

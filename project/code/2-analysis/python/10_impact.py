"""10: Dampak (Q12), semua angka berlabel estimated.

NG terhindari per bulan = (NG rate supplier terburuk - NG rate pembanding) x volume bulanan supplier itu.
Asumsi (docs/scorecard_definition.md): "rata-rata supplier lain" = NG rate gabungan (berbobot unit) supplier lain; volume bulanan =
rata-rata unit per bulan pada 4 bulan penuh (April sampai Juli); Agustus tidak lengkap. Sensitivitas: pembanding rata-rata sederhana
dan volume semua bulan. CI bootstrap atas lot. Hasil: results/2-analysis/impact_scenarios.csv, impact_monthly.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import common as CM

R = CM.RES2
rng = np.random.default_rng(CM.SEED + 12)
usage = pd.read_csv(R / "usage_detail.csv")
lots = pd.read_csv(R / "lot_level.csv")
sup = pd.read_csv(R / "ng_supplier.csv").set_index("supplier_code")
nm = pd.read_csv(R / "ng_month.csv")
FULL = ["2026-04", "2026-05", "2026-06", "2026-07"]
worst = sup.sort_values(["ng_rate"], ascending=False).index[0]


def pooled_other(df, s):
    o = df[df.supplier_code != s]
    return o.ng.sum() / o.units.sum()


def boot_diff(s, B=CM.BOOT_B):
    a, b = lots[lots.supplier_code == s], lots[lots.supplier_code != s]
    ua, ga, ub, gb = (x.to_numpy(float) for x in (a.units, a.ng, b.units, b.ng))
    ia = rng.integers(0, len(a), size=(B, len(a)))
    ib = rng.integers(0, len(b), size=(B, len(b)))
    d = ga[ia].sum(1) / ua[ia].sum(1) - gb[ib].sum(1) / ub[ib].sum(1)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


rows = []
vol_full = float(nm[(nm.supplier_code == worst) & nm.month.isin(FULL)].units.mean())
vol_all = float(nm[nm.supplier_code == worst].units.mean())
simple_other = float(sup.drop(worst).ng_rate.mean())
r_w = float(sup.loc[worst, "ng_rate"])
pool = float(pooled_other(lots, worst))
lo, hi = boot_diff(worst)
for label, ref, vol, ci in (
    ("dasar: pembanding gabungan, volume 4 bulan penuh", pool, vol_full, (lo, hi)),
    ("sensitivitas: pembanding rata-rata sederhana supplier lain", simple_other, vol_full, None),
    ("sensitivitas: volume rata-rata semua bulan (Agustus tidak lengkap)", pool, vol_all, None),
):
    d = r_w - ref
    rows.append(dict(skenario=label, supplier=worst, ng_rate_supplier=r_w, ng_rate_pembanding=ref, selisih=d, volume_bulanan=vol,
                     ng_terhindari_per_bulan=d * vol, ci_low=(ci[0] * vol if ci else np.nan), ci_high=(ci[1] * vol if ci else np.nan),
                     persen_ng_supplier_terhindari=d / r_w, label="estimated"))
# supplier yang memburuk: kembali ke NG rate sebelum 8 minggu terakhir
q6 = pd.read_csv(R / "q6_worsening.csv")
for r in q6[q6.memburuk == 1].itertuples():
    vol = float(nm[(nm.supplier_code == r.supplier_code) & nm.month.isin(FULL)].units.mean())
    d = r.ng_rate_terkini - r.ng_rate_sebelumnya
    rows.append(dict(skenario=f"tambahan: {r.supplier_code} kembali ke NG rate sebelum memburuk", supplier=r.supplier_code,
                     ng_rate_supplier=r.ng_rate_terkini, ng_rate_pembanding=r.ng_rate_sebelumnya, selisih=d, volume_bulanan=vol,
                     ng_terhindari_per_bulan=d * vol, ci_low=np.nan, ci_high=np.nan, persen_ng_supplier_terhindari=d / r.ng_rate_terkini, label="estimated"))
pd.DataFrame(rows).to_csv(R / "impact_scenarios.csv", index=False, float_format="%.10g")
# total NG material per bulan semua supplier (konteks)
tot = nm[nm.month.isin(FULL)].groupby("month").agg(units=("units", "sum"), ng=("ng", "sum")).reset_index()
tot["ng_terhindari_skenario_dasar"] = rows[0]["ng_terhindari_per_bulan"]
tot["persen_dari_total_ng"] = tot.ng_terhindari_skenario_dasar / tot.ng
tot.to_csv(R / "impact_monthly.csv", index=False, float_format="%.10g")
print(pd.DataFrame(rows)[["skenario", "ng_terhindari_per_bulan", "ci_low", "ci_high"]].to_string(index=False))

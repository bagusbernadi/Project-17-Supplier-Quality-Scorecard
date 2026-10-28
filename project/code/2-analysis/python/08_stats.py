"""08: Uji statistik Q1 sampai Q9 dan keputusan hipotesis H1 sampai H5.

Kriteria keputusan hipotesis ditetapkan di sini (dan di docs/scorecard_definition.md) sebelum hasil dilihat.
Catatan metodologi: baris pemakaian dalam satu lot tidak independen, sehingga uji tingkat unit (chi-square, z)
cenderung terlalu yakin. Setiap uji unit dipasangkan dengan uji tingkat lot (Mann-Whitney / Kruskal-Wallis atas NG rate lot)
dan CI bootstrap per lot sebagai pembanding.
Hasil (results/2-analysis): q1_ng_rate_ci.csv, q1_top_per_material.csv, q2_tests.csv, q3_rank_summary.csv,
q4_lot_variation.csv, q4_pchart_lots.csv, q5_lot_threshold.csv, q6_worsening.csv, q7_month_change.csv,
q8_cross_tests.csv, q8_adjusted_or.csv, q9_min_units.csv, q9_supplier_month_ci.csv, concentration_lots.csv, hypotheses.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint
import common as CM

rng = np.random.default_rng(CM.SEED)
R = CM.RES2
usage = pd.read_csv(R / "usage_detail.csv", parse_dates=["date", "week_start"])
lots = pd.read_csv(R / "lot_level.csv")
sm_tab = pd.read_csv(R / "ng_supplier_material.csv")
nm = pd.read_csv(R / "ng_month.csv")
weekly = pd.read_csv(R / "rolling_weekly.csv", parse_dates=["week_start"])
lotcv = pd.read_csv(R / "lot_cv.csv")
suppliers = sorted(usage.supplier_code.unique())
materials = sorted(usage.material_code.unique())
lots_eval = lots[lots.units >= CM.LOT_MIN_UNITS].copy()


def wilson(k, n):
    lo, hi = proportion_confint(int(k), int(n), alpha=CM.ALPHA, method="wilson")
    return float(lo), float(hi)


def z_two_prop(k1, n1, k2, n2, alt="greater"):
    p1, p2, p = k1 / n1, k2 / n2, (k1 + k2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    if alt == "greater":
        return float(z), float(1 - stats.norm.cdf(z))
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))


def holm(ps):
    return multipletests(ps, method="holm")[1] if len(ps) else np.array([])


# ---------------- Q1: NG rate dengan CI Wilson dan CI bootstrap per lot ----------------
def boot_ci(df, B=CM.BOOT_B):
    u, g = df.units.to_numpy(float), df.ng.to_numpy(float)
    idx = rng.integers(0, len(df), size=(B, len(df)))
    r = g[idx].sum(1) / u[idx].sum(1)
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


rows = []
for s in suppliers:
    d = lots[lots.supplier_code == s]
    k, n = int(d.ng.sum()), int(d.units.sum())
    lo, hi = wilson(k, n); blo, bhi = boot_ci(d)
    rows.append(dict(tingkat="supplier", supplier_code=s, material_code="semua", units=n, ng=k, ng_rate=k / n, ci_low=lo, ci_high=hi,
                     ci_boot_lot_low=blo, ci_boot_lot_high=bhi, lots=len(d)))
for r in sm_tab.itertuples():
    d = lots[(lots.supplier_code == r.supplier_code) & (lots.material_code == r.material_code)]
    lo, hi = wilson(r.ng, r.units); blo, bhi = boot_ci(d)
    rows.append(dict(tingkat="supplier x material", supplier_code=r.supplier_code, material_code=r.material_code, units=int(r.units),
                     ng=int(r.ng), ng_rate=r.ng / r.units, ci_low=lo, ci_high=hi, ci_boot_lot_low=blo, ci_boot_lot_high=bhi, lots=len(d)))
q1 = pd.DataFrame(rows)
q1.to_csv(R / "q1_ng_rate_ci.csv", index=False, float_format="%.10g")

# tertinggi per material: perbandingan dengan supplier lain pada material yang sama (z satu sisi, Holm; uji lot Mann-Whitney)
top_rows = []
for m in materials:
    g = q1[(q1.tingkat == "supplier x material") & (q1.material_code == m)].sort_values(["ng_rate", "supplier_code"], ascending=[False, True])
    top = g.iloc[0]
    others = g.iloc[1:]
    pz, pm = [], []
    for o in others.itertuples():
        pz.append(z_two_prop(top.ng, top.units, o.ng, o.units)[1])
        a = lots_eval[(lots_eval.supplier_code == top.supplier_code) & (lots_eval.material_code == m)].ng_rate
        b = lots_eval[(lots_eval.supplier_code == o.supplier_code) & (lots_eval.material_code == m)].ng_rate
        pm.append(float(stats.mannwhitneyu(a, b, alternative="greater").pvalue))
    hz, hm = (holm(pz), holm(pm)) if len(pz) else (np.array([]), np.array([]))
    top_rows.append(dict(material_code=m, supplier_tertinggi=top.supplier_code, ng_rate=top.ng_rate, ci_low=top.ci_low, ci_high=top.ci_high,
                         pembanding=len(others), p_unit_holm_maks=float(hz.max()) if len(hz) else np.nan,
                         p_lot_holm_maks=float(hm.max()) if len(hm) else np.nan,
                         supplier_kedua=others.iloc[0].supplier_code if len(others) else "", ng_rate_kedua=others.iloc[0].ng_rate if len(others) else np.nan))
q1top = pd.DataFrame(top_rows)
q1top.to_csv(R / "q1_top_per_material.csv", index=False, float_format="%.10g")

# ---------------- Q2: chi-square antar supplier ----------------
def chi_row(name, df):
    tab = np.array([df.ng.to_numpy(), (df.units - df.ng).to_numpy()])
    chi2, p, dof, _ = stats.chi2_contingency(tab)
    n = tab.sum()
    v = float(np.sqrt(chi2 / (n * (min(tab.shape) - 1))))
    return dict(uji=name, statistik=float(chi2), derajat_bebas=int(dof), p_value=float(p), effect_size_cramers_v=v, n_unit=int(n))


tests = [chi_row("chi-square NG vs OK antar 5 supplier (unit)", q1[q1.tingkat == "supplier"])]
for m in materials:
    g = q1[(q1.tingkat == "supplier x material") & (q1.material_code == m)]
    tests.append(chi_row(f"chi-square antar supplier pada {m} (unit)", g))
kw = stats.kruskal(*[lots_eval[lots_eval.supplier_code == s].ng_rate for s in suppliers])
tests.append(dict(uji="Kruskal-Wallis NG rate lot antar 5 supplier (lot)", statistik=float(kw.statistic), derajat_bebas=len(suppliers) - 1,
                  p_value=float(kw.pvalue), effect_size_cramers_v=np.nan, n_unit=len(lots_eval)))
q2 = pd.DataFrame(tests)
q2.to_csv(R / "q2_tests.csv", index=False, float_format="%.10g")

# ---------------- Q3: ringkasan ranking bulanan ----------------
rows = []
for s in suppliers:
    d = nm[nm.supplier_code == s].sort_values("month")
    rk = d.rank_ng.to_numpy()
    rows.append(dict(supplier_code=s, rank_rata_rata=float(rk.mean()), rank_terbaik=int(rk.min()), rank_terburuk=int(rk.max()),
                     bulan_rank_1=int((rk == 1).sum()), perubahan_rank=int((np.diff(rk) != 0).sum()), jumlah_bulan=len(rk)))
pd.DataFrame(rows).to_csv(R / "q3_rank_summary.csv", index=False, float_format="%.10g")

# ---------------- Q4: variasi antar lot dan p-chart ----------------
pbar = lots.groupby("supplier_code").apply(lambda d: d.ng.sum() / d.units.sum(), include_groups=False).to_dict()
le = lots_eval.copy()
le["p_bar"] = le.supplier_code.map(pbar)
le["ucl"] = le.p_bar + 3 * np.sqrt(le.p_bar * (1 - le.p_bar) / le.units)
le["di_atas_ucl"] = (le.ng_rate > le.ucl).astype(int)
le[le.di_atas_ucl == 1].sort_values(["supplier_code", "ng_rate", "lot_code"], ascending=[True, False, True])[
    ["lot_code", "supplier_code", "material_code", "units", "ng", "ng_rate", "p_bar", "ucl"]].to_csv(R / "q4_pchart_lots.csv", index=False, float_format="%.10g")
q4 = lotcv.merge(le.groupby("supplier_code").agg(lot_di_atas_ucl=("di_atas_ucl", "sum")).reset_index(), on="supplier_code")
q4["persen_lot_di_atas_ucl"] = q4.lot_di_atas_ucl / q4.lots_eval
# dispersi berlebih: varians NG rate antar lot dibanding varians binomial murni
od = le.groupby("supplier_code").apply(lambda d: float(((d.ng_rate - d.p_bar) ** 2 / (d.p_bar * (1 - d.p_bar) / d.units)).mean()), include_groups=False)
q4["dispersi_berlebih"] = q4.supplier_code.map(od)
q4.to_csv(R / "q4_lot_variation.csv", index=False, float_format="%.10g")

# ---------------- Q5: persen lot di atas ambang (dengan sensitivitas) ----------------
rows = []
for thr in (0.015, CM.LOT_THRESHOLD, 0.03):
    for s in suppliers:
        d = lots_eval[lots_eval.supplier_code == s]
        k = int((d.ng_rate > thr).sum()); n = len(d)
        lo, hi = wilson(k, n)
        rows.append(dict(ambang=thr, supplier_code=s, lot_dinilai=n, lot_di_atas_ambang=k, persen=k / n, ci_low=lo, ci_high=hi, dasar=int(thr == CM.LOT_THRESHOLD)))
pd.DataFrame(rows).to_csv(R / "q5_lot_threshold.csv", index=False, float_format="%.10g")

# ---------------- Q6: supplier yang memburuk (8 minggu terakhir vs sebelumnya) ----------------
RECENT_WEEKS, WORSEN_RATIO = 8, 1.5                      # asumsi, lihat docs/scorecard_definition.md
wk_all = sorted(weekly.week_start.unique())
cut = wk_all[-RECENT_WEEKS]
rows = []
for s in suppliers:
    d = weekly[weekly.supplier_code == s]
    rec, base = d[d.week_start >= cut], d[d.week_start < cut]
    k1, n1, k0, n0 = rec.ng.sum(), rec.units.sum(), base.ng.sum(), base.units.sum()
    z, p = z_two_prop(k1, n1, k0, n0)
    rows.append(dict(supplier_code=s, ng_rate_terkini=k1 / n1, ng_rate_sebelumnya=k0 / n0, rasio=(k1 / n1) / (k0 / n0), z=z, p_satu_sisi=p,
                     rolling_4w_terakhir=float(d.sort_values("week_start").rolling_ng_rate.iloc[-1])))
q6 = pd.DataFrame(rows)
q6["p_holm"] = holm(q6.p_satu_sisi.to_numpy())
q6["memburuk"] = ((q6.p_holm < CM.ALPHA) & (q6.rasio >= WORSEN_RATIO)).astype(int)
q6["awal_periode_terkini"] = pd.Timestamp(cut).strftime("%Y-%m-%d")
q6.to_csv(R / "q6_worsening.csv", index=False, float_format="%.10g")

# ---------------- Q7: perubahan antar bulan (dua proporsi, Holm atas semua uji) ----------------
rows = []
for s in suppliers:
    d = nm[nm.supplier_code == s].sort_values("month").reset_index(drop=True)
    for i in range(1, len(d)):
        a, b = d.iloc[i], d.iloc[i - 1]
        if a.units > 0 and b.units > 0:
            z, p = z_two_prop(a.ng, a.units, b.ng, b.units, alt="two")
            rows.append(dict(supplier_code=s, bulan=a.month, bulan_sebelumnya=b.month, ng_rate=a.ng / a.units, ng_rate_sebelumnya=b.ng / b.units,
                             selisih=a.ng / a.units - b.ng / b.units, z=z, p_dua_sisi=p))
q7 = pd.DataFrame(rows)
q7["p_holm"] = holm(q7.p_dua_sisi.to_numpy())
q7["nyata"] = (q7.p_holm < CM.ALPHA).astype(int)
q7.to_csv(R / "q7_month_change.csv", index=False, float_format="%.10g")

# ---------------- Q8: model dan stasiun; regresi logistik terkoreksi ----------------
rows = []
for s in suppliers:
    for dim in ("model_code", "station_code"):
        d = usage[usage.supplier_code == s].groupby(dim).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum"))
        chi2, p, dof, _ = stats.chi2_contingency(np.array([d.ng, d.units - d.ng]))
        rows.append(dict(supplier_code=s, dimensi=dim, chi2=float(chi2), derajat_bebas=int(dof), p_value=float(p),
                         ng_rate_tertinggi=float((d.ng / d.units).max()), ng_rate_terendah=float((d.ng / d.units).min())))
pd.DataFrame(rows).to_csv(R / "q8_cross_tests.csv", index=False, float_format="%.10g")

cells = usage.groupby(["supplier_code", "model_code", "station_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index()
cells["ok"] = cells.units - cells.ng
rows = []
ref_rates = lots.groupby("supplier_code").apply(lambda d: d.ng.sum() / d.units.sum(), include_groups=False)
for s in suppliers:
    cells["is_s"] = (cells.supplier_code == s).astype(int)
    f0 = smf.glm("ng + ok ~ is_s", data=cells, family=sm.families.Binomial()).fit(scale="X2")
    f1 = smf.glm("ng + ok ~ is_s + C(model_code) + C(station_code)", data=cells, family=sm.families.Binomial()).fit(scale="X2")
    b0, b1 = f0.params["is_s"], f1.params["is_s"]
    ci0, ci1 = f0.conf_int().loc["is_s"], f1.conf_int().loc["is_s"]
    rows.append(dict(supplier_code=s, or_tanpa_koreksi=float(np.exp(b0)), or_tanpa_low=float(np.exp(ci0[0])), or_tanpa_high=float(np.exp(ci0[1])),
                     or_terkoreksi=float(np.exp(b1)), or_terkoreksi_low=float(np.exp(ci1[0])), or_terkoreksi_high=float(np.exp(ci1[1])),
                     p_terkoreksi=float(f1.pvalues["is_s"]),
                     persen_selisih_dijelaskan=float(1 - b1 / b0) if abs(b0) > 1e-9 else np.nan, ng_rate=float(ref_rates[s])))
q8 = pd.DataFrame(rows)
q8.to_csv(R / "q8_adjusted_or.csv", index=False, float_format="%.10g")

# ---------------- Q9: jumlah unit minimum ----------------
overall = float(lots.ng.sum() / lots.units.sum())
rows = []
for n in (500, 1000, 2000, 3000, 5000, 8000, 12000, 20000, 50000):
    for label, p in (("rata-rata semua supplier", overall), ("supplier terbaik", float(ref_rates.min())), ("supplier terburuk", float(ref_rates.max()))):
        lo, hi = wilson(round(p * n), n)
        rows.append(dict(units=n, acuan=label, ng_rate=p, ci_low=lo, ci_high=hi, setengah_lebar_relatif=(hi - lo) / 2 / p))
pd.DataFrame(rows).to_csv(R / "q9_min_units.csv", index=False, float_format="%.10g")
rows = []
for r in nm.itertuples():
    if r.units > 0:
        lo, hi = wilson(r.ng, r.units)
        rows.append(dict(month=r.month, supplier_code=r.supplier_code, units=int(r.units), lots=int(r.lots), ng_rate=r.ng_rate, ci_low=lo, ci_high=hi,
                         setengah_lebar_relatif=(hi - lo) / 2 / r.ng_rate if r.ng_rate > 0 else np.nan,
                         memenuhi_batas_sampel=int(r.units >= CM.MIN_UNITS and r.lots >= CM.MIN_LOTS)))
q9 = pd.DataFrame(rows)
q9.to_csv(R / "q9_supplier_month_ci.csv", index=False, float_format="%.10g")


def min_units(p, rel=CM.REL_HALFWIDTH_OK):
    for n in range(100, 2_000_000, 100):
        lo, hi = wilson(round(p * n), n)
        if (hi - lo) / 2 / p <= rel:
            return n
    return np.nan


# ---------------- Konsentrasi NG pada sedikit lot (H2) ----------------
TOP_SHARE = 0.10
rows = []
for s in suppliers:
    d = lots[lots.supplier_code == s].sort_values(["ng", "lot_code"], ascending=[False, True])
    k = max(1, int(round(TOP_SHARE * len(d))))
    share = float(d.ng.iloc[:k].sum() / d.ng.sum())
    sims = []
    for _ in range(500):                          # pembanding: semua lot sama (NG ~ binomial menurut unit lot)
        ng_sim = rng.binomial(d.units.to_numpy(), d.ng.sum() / d.units.sum())
        sims.append(np.sort(ng_sim)[::-1][:k].sum() / max(ng_sim.sum(), 1))
    rows.append(dict(supplier_code=s, lots=len(d), lot_teratas=k, persen_ng_dari_lot_teratas=share,
                     pembanding_lot_seragam=float(np.mean(sims)), melebihi_50persen=int(share > 0.5)))
conc = pd.DataFrame(rows)
conc.to_csv(R / "concentration_lots.csv", index=False, float_format="%.10g")

# ---------------- Keputusan hipotesis (kriteria tetap) ----------------
hy = []
# H1: ada material dengan supplier tertinggi yang signifikan lebih tinggi dari semua pembanding pada tingkat unit DAN lot
h1_unit = q1top[(q1top.pembanding >= 1) & (q1top.p_unit_holm_maks < CM.ALPHA)]
h1_lot = q1top[(q1top.pembanding >= 1) & (q1top.p_lot_holm_maks < CM.ALPHA)]
both = sorted(set(h1_unit.material_code) & set(h1_lot.material_code))
if both:
    v1 = "Terbukti"
elif len(h1_unit):
    v1 = "Belum bisa disimpulkan"
else:
    v1 = "Tidak terbukti"
hy.append(dict(id="H1", hipotesis_rancangan="Satu supplier punya NG rate yang lebih tinggi secara signifikan untuk jenis material yang sama.",
               bukti=f"material dengan supplier tertinggi signifikan pada tingkat unit: {len(h1_unit)} dari {len(q1top)}; pada tingkat lot: {len(h1_lot)}; keduanya: {len(both)}",
               verdict=v1, catatan_keputusan="Terbukti bila signifikan (Holm, alfa 0,05) pada tingkat unit dan tingkat lot; Belum bisa disimpulkan bila hanya tingkat unit."))
# H2
n_conc = int(conc.melebihi_50persen.sum())
v2 = "Terbukti" if n_conc >= 3 else "Tidak terbukti"
hy.append(dict(id="H2", hipotesis_rancangan="Sebagian besar NG suatu supplier berasal dari sedikit lot, bukan merata di semua lot.",
               bukti=f"{n_conc} dari {len(conc)} supplier punya lebih dari 50% NG dari 10% lot teratas; rentang {conc.persen_ng_dari_lot_teratas.min():.1%} sampai {conc.persen_ng_dari_lot_teratas.max():.1%}",
               verdict=v2, catatan_keputusan="Terbukti bila lebih dari 50% NG berasal dari 10% lot teratas pada sedikitnya 3 dari 5 supplier."))
# H3
n_w = int(q6.memburuk.sum())
v3 = "Terbukti" if n_w >= 1 else "Tidak terbukti"
w_list = ", ".join(q6[q6.memburuk == 1].supplier_code) or "tidak ada"
hy.append(dict(id="H3", hipotesis_rancangan="Satu supplier memburuk dalam beberapa bulan terakhir, terlihat dari rolling NG rate.",
               bukti=f"supplier memburuk (8 minggu terakhir vs sebelumnya, rasio >= 1,5, Holm p < 0,05): {w_list}",
               verdict=v3, catatan_keputusan="Terbukti bila sedikitnya satu supplier memenuhi kedua syarat."))
# H4: supplier terburuk vs lainnya
worst = q8.sort_values(["ng_rate", "supplier_code"], ascending=[False, True]).iloc[0]
exp_pct = float(worst.persen_selisih_dijelaskan)
v4 = "Terbukti" if exp_pct >= 0.10 else "Tidak terbukti"
hy.append(dict(id="H4", hipotesis_rancangan="Sebagian perbedaan antar supplier hilang setelah model dan stasiun pemakai diperhitungkan.",
               bukti=f"supplier terburuk {worst.supplier_code}: OR {worst.or_tanpa_koreksi:.2f} menjadi {worst.or_terkoreksi:.2f}; {exp_pct:.1%} selisih (skala log) dijelaskan model dan stasiun",
               verdict=v4, catatan_keputusan="Terbukti bila model dan stasiun menjelaskan sedikitnya 10% selisih (log odds ratio) supplier terburuk."))
# H5: supplier volume terendah
vol = lots.groupby("supplier_code").units.sum().sort_values()
small = vol.index[0]
sm_m = q9[q9.supplier_code == small]
frac_wide = float((sm_m.setengah_lebar_relatif > CM.REL_HALFWIDTH_OK).mean())
frac_ns = float((sm_m.memenuhi_batas_sampel == 0).mean())
v5 = "Terbukti" if frac_wide >= 0.5 else "Tidak terbukti"
hy.append(dict(id="H5", hipotesis_rancangan="Supplier dengan volume kecil punya rentang keyakinan yang terlalu lebar untuk diberi status.",
               bukti=f"supplier volume terkecil {small}: CI bulanan terlalu lebar (setengah lebar > 25% dari NG rate) pada {frac_wide:.0%} bulan; {frac_ns:.0%} bulan di bawah batas 2.000 unit atau 10 lot",
               verdict=v5, catatan_keputusan="Terbukti bila setengah lebar CI Wilson bulanan supplier terkecil lebih dari 25% NG rate pada sedikitnya separuh bulan."))
pd.DataFrame(hy).to_csv(R / "hypotheses.csv", index=False)

# unit minimum untuk batas lebar relatif 25%
pd.DataFrame([dict(acuan=l, ng_rate=p, unit_minimum=min_units(p)) for l, p in
              (("rata-rata semua supplier", overall), ("supplier terbaik", float(ref_rates.min())), ("supplier terburuk", float(ref_rates.max())))]
             ).to_csv(R / "q9_unit_minimum.csv", index=False, float_format="%.10g")
print(pd.DataFrame(hy)[["id", "verdict", "bukti"]].to_string(index=False))

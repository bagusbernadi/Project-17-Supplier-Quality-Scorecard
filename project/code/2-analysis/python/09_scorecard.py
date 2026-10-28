"""09: Skor dan status scorecard bulanan (Q10), sensitivitas bobot dan konstanta (Q11), dukungan uji untuk status merah.

Sub-skor dan skor dihitung di pandas dari komponen hasil SQL (score_components.csv), lalu dihitung ulang dengan SQL
sebagai cek. Tabel scorecard_monthly disimpan ke database. Definisi: docs/scorecard_definition.md.
Hasil (results/2-analysis): scorecard_monthly.csv, scorecard_latest.csv, red_support.csv, sensitivity_weights.csv,
sensitivity_grid.csv, sensitivity_scale.csv, sensitivity_summary.csv
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint
import common as CM

R = CM.RES2
comp = pd.read_csv(R / "score_components.csv")
usage = pd.read_csv(R / "usage_detail.csv")


def sub_scores(df, ng0=CM.NG_RATE_ZERO_SCORE, cv0=CM.CV_ZERO_SCORE, tr0=CM.TREND_ZERO_SCORE):
    out = pd.DataFrame(index=df.index)
    out["s_ng"] = 100 * np.clip(1 - df.ng_rate / ng0, 0, 1)
    out["s_cons"] = 100 * np.clip(1 - df.lot_cv / cv0, 0, 1)
    out["s_trend"] = 100 * np.clip(1 - np.clip(df.trend_rel, 0, None) / tr0, 0, 1)
    return out


def combine(sub, w):
    """Skor tertimbang; sub-skor kosong (NaN) dilewati dan bobot dinormalkan ulang."""
    ws = pd.Series({"s_ng": w["ng"], "s_cons": w["cons"], "s_trend": w["trend"]})
    ok = sub.notna()
    num = (sub.fillna(0) * ws).sum(axis=1)
    den = (ok * ws).sum(axis=1)
    return num / den


def status_of(score, rated):
    s = np.where(score >= CM.GREEN, "hijau", np.where(score >= CM.YELLOW, "kuning", "merah"))
    return np.where(rated, s, "belum dinilai")


comp["rated"] = (comp.units >= CM.MIN_UNITS) & (comp.lots >= CM.MIN_LOTS)
sub = sub_scores(comp)
comp = pd.concat([comp, sub], axis=1)
comp["score"] = combine(comp[["s_ng", "s_cons", "s_trend"]], CM.WEIGHTS)
comp["status"] = status_of(comp.score, comp.rated)
lo_hi = [proportion_confint(int(k), int(n), alpha=CM.ALPHA, method="wilson") if n > 0 else (np.nan, np.nan) for k, n in zip(comp.ng, comp.units)]
comp["ci_low"] = [a for a, b in lo_hi]
comp["ci_high"] = [b for a, b in lo_hi]
comp.loc[~comp.rated, ["score"]] = np.nan                        # tidak diberi skor bila belum dinilai
sc = comp[["month", "supplier_code", "units", "lots", "ng", "ng_rate", "ci_low", "ci_high", "lots_eval", "lot_cv", "trend_rel",
           "s_ng", "s_cons", "s_trend", "score", "status"]].rename(columns={"trend_rel": "trend"})
sc["score"] = sc.score.round(8)
for c in ("s_ng", "s_cons", "s_trend"):
    sc[c] = sc[c].round(8)
sc.to_csv(R / "scorecard_monthly.csv", index=False, float_format="%.10g")

# ---- simpan ke database dan cek ulang dengan SQL ----
con = duckdb.connect(str(CM.DB_PATH))
con.execute("DROP TABLE IF EXISTS scorecard_monthly")
con.register("sc_df", sc)
con.execute("CREATE TABLE scorecard_monthly AS SELECT * FROM sc_df")
# hitung ulang skor dan status dengan SQL murni dari komponen
chk = con.execute(f"""
WITH s AS (
  SELECT month, supplier_code,
    100 * least(1, greatest(0, 1 - ng_rate / {CM.NG_RATE_ZERO_SCORE})) AS s_ng,
    100 * least(1, greatest(0, 1 - lot_cv / {CM.CV_ZERO_SCORE})) AS s_cons,
    CASE WHEN trend IS NULL THEN NULL ELSE 100 * least(1, greatest(0, 1 - greatest(0, trend) / {CM.TREND_ZERO_SCORE})) END AS s_trend,
    units, lots
  FROM scorecard_monthly
), t AS (
  SELECT *, (s_ng * {CM.WEIGHTS['ng']} + s_cons * {CM.WEIGHTS['cons']} + coalesce(s_trend, 0) * {CM.WEIGHTS['trend']})
            / ({CM.WEIGHTS['ng']} + {CM.WEIGHTS['cons']} + CASE WHEN s_trend IS NULL THEN 0 ELSE {CM.WEIGHTS['trend']} END) AS score_sql
  FROM s WHERE units >= {CM.MIN_UNITS} AND lots >= {CM.MIN_LOTS}
)
SELECT t.month, t.supplier_code, t.score_sql, m.score,
       CASE WHEN t.score_sql >= {CM.GREEN} THEN 'hijau' WHEN t.score_sql >= {CM.YELLOW} THEN 'kuning' ELSE 'merah' END AS status_sql, m.status
FROM t JOIN scorecard_monthly m USING (month, supplier_code) ORDER BY 1, 2
""").df()
con.close()
chk["selisih"] = (chk.score_sql - chk.score).abs()
assert (chk.selisih < 1e-6).all() and (chk.status_sql == chk.status).all(), "skor SQL dan pandas berbeda"
pd.DataFrame([dict(pengecekan="skor dan status SQL vs pandas", baris=len(chk), cocok=int(((chk.selisih < 1e-6) & (chk.status_sql == chk.status)).sum()))]
             ).to_csv(R / "scorecard_crosscheck.csv", index=False)

# ---- scorecard terakhir (Q10) ----
months = sorted(sc.month.unique())
last = months[-1]
mean_score = sc[sc.score.notna()].groupby("supplier_code").score.mean()
n_red = sc[sc.status == "merah"].groupby("supplier_code").size()
n_rated = sc[sc.status != "belum dinilai"].groupby("supplier_code").size()
lat = sc[sc.month == last].copy()
lat["skor_rata_rata_bulan"] = lat.supplier_code.map(mean_score)
lat["bulan_merah"] = lat.supplier_code.map(n_red).fillna(0).astype(int)
lat["bulan_dinilai"] = lat.supplier_code.map(n_rated).fillna(0).astype(int)
lat.to_csv(R / "scorecard_latest.csv", index=False, float_format="%.10g")

# ---- dukungan uji untuk status merah ----
lm = usage.groupby(["month", "lot_code", "supplier_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index()
lm = lm[lm.units >= CM.LOT_MIN_UNITS]
lm["r"] = lm.ng / lm.units
rows = []
for r in sc[sc.status == "merah"].itertuples():
    oth = sc[(sc.month == r.month) & (sc.supplier_code != r.supplier_code)]
    k1, n1, k0, n0 = r.ng, r.units, oth.ng.sum(), oth.units.sum()
    p = (k1 + k0) / (n1 + n0)
    z = (k1 / n1 - k0 / n0) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    pz = 1 - stats.norm.cdf(z)
    a = lm[(lm.month == r.month) & (lm.supplier_code == r.supplier_code)].r
    b = lm[(lm.month == r.month) & (lm.supplier_code != r.supplier_code)].r
    pm = float(stats.mannwhitneyu(a, b, alternative="greater").pvalue)
    rows.append(dict(month=r.month, supplier_code=r.supplier_code, score=r.score, ng_rate=r.ng_rate, ng_rate_lainnya=k0 / n0,
                     p_unit=float(pz), p_lot=pm))
rs = pd.DataFrame(rows)
if len(rs):
    rs["p_unit_holm"] = multipletests(rs.p_unit, method="holm")[1]
    rs["p_lot_holm"] = multipletests(rs.p_lot, method="holm")[1]
    rs["didukung"] = ((rs.p_unit_holm < CM.ALPHA) & (rs.p_lot_holm < CM.ALPHA)).astype(int)
else:
    rs = pd.DataFrame(columns=["month", "supplier_code", "score", "ng_rate", "ng_rate_lainnya", "p_unit", "p_lot", "p_unit_holm", "p_lot_holm", "didukung"])
rs.to_csv(R / "red_support.csv", index=False, float_format="%.10g")

# ---- sensitivitas bobot (Q11) ----
def ranks(df, w, **kw):
    s = combine(sub_scores(df, **kw), w)
    return s


tgt = {}
base_m = comp[(comp.month == last) & comp.rated].set_index("supplier_code")
tgt["bulan terakhir"] = base_m
avg = comp[comp.rated].groupby("supplier_code").agg(ng_rate=("ng_rate", "mean"), lot_cv=("lot_cv", "mean"), trend_rel=("trend_rel", "mean"))
tgt["rata-rata bulan dinilai"] = avg


def tau(a, b):
    return float(stats.kendalltau(a, b).statistic)


rows = []
for name, df in tgt.items():
    for wng in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        rest = (1 - wng) / 2
        s = combine(sub_scores(df), dict(ng=wng, cons=rest, trend=rest))
        rk = s.rank(ascending=False, method="min")
        for sup in df.index:
            rows.append(dict(sasaran=name, bobot_ng=wng, supplier_code=sup, skor=float(s[sup]), ranking=int(rk[sup]),
                             status=str(status_of(pd.Series([s[sup]]), np.array([True]))[0])))
pd.DataFrame(rows).to_csv(R / "sensitivity_weights.csv", index=False, float_format="%.10g")

grid = [(a / 20, b / 20, (20 - a - b) / 20) for a in range(2, 17) for b in range(2, 17) if 2 <= 20 - a - b <= 16]
rows = []
for name, df in tgt.items():
    base = combine(sub_scores(df), CM.WEIGHTS)
    base_rank = base.rank(ascending=False, method="min")
    base_status = pd.Series(status_of(base, np.ones(len(base), bool)), index=base.index)
    same_order = same_top = same_low = 0
    taus, chg = [], {s: 0 for s in df.index}
    for wn, wc, wt in grid:
        s = combine(sub_scores(df), dict(ng=wn, cons=wc, trend=wt))
        rk = s.rank(ascending=False, method="min")
        same_order += int((rk == base_rank).all())
        same_top += int(rk.idxmin() == base_rank.idxmin())
        same_low += int(rk.idxmax() == base_rank.idxmax())
        taus.append(tau(base, s))
        st = pd.Series(status_of(s, np.ones(len(s), bool)), index=s.index)
        for sup in df.index:
            chg[sup] += int(st[sup] != base_status[sup])
    n = len(grid)
    rows.append(dict(sasaran=name, kombinasi_bobot=n, urutan_sama_persen=same_order / n, supplier_teratas_sama_persen=same_top / n, supplier_terendah_sama_persen=same_low / n,
                     tau_kendall_min=float(np.min(taus)), tau_kendall_rata=float(np.mean(taus)),
                     **{f"status_berubah_{s}": chg[s] / n for s in df.index}))
pd.DataFrame(rows).to_csv(R / "sensitivity_grid.csv", index=False, float_format="%.10g")

# ---- sensitivitas konstanta skala ----
rows = []
for name, df in tgt.items():
    base = combine(sub_scores(df), CM.WEIGHTS)
    for f in (0.5, 1.0, 2.0):
        s = combine(sub_scores(df, ng0=CM.NG_RATE_ZERO_SCORE * f, cv0=CM.CV_ZERO_SCORE * f, tr0=CM.TREND_ZERO_SCORE * f), CM.WEIGHTS)
        rk = s.rank(ascending=False, method="min")
        st = status_of(s, np.ones(len(s), bool))
        for i, sup in enumerate(df.index):
            rows.append(dict(sasaran=name, faktor_skala=f, supplier_code=sup, skor=float(s[sup]), ranking=int(rk[sup]), status=str(st[i]),
                             tau_vs_dasar=tau(base, s)))
pd.DataFrame(rows).to_csv(R / "sensitivity_scale.csv", index=False, float_format="%.10g")
print(lat[["supplier_code", "units", "ng_rate", "score", "status", "skor_rata_rata_bulan", "bulan_merah"]].to_string(index=False))
print(rs.to_string(index=False))
print(pd.read_csv(R / "sensitivity_grid.csv").T.to_string())

"""06: Cek silang SQL vs pandas. Semua ukuran dari 05 (view SQL) dihitung ulang dengan pandas dari data bersih
(data/clean), lalu dibandingkan. Hasil harus cocok pada setiap pemeriksaan (toleransi 1e-8).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import common as C

lot = pd.read_csv(C.CLEAN / "material_lot_clean.csv")
use = pd.read_csv(C.CLEAN / "lot_usage_clean.csv", parse_dates=["date"])
u = use.merge(lot[["lot_code", "supplier_code", "material_code"]], on="lot_code")
u["month"] = u["date"].dt.strftime("%Y-%m")
u["week_start"] = (u["date"] - pd.to_timedelta(u["date"].dt.weekday, unit="D")).dt.normalize()
suppliers = sorted(lot.supplier_code.unique())
months = sorted(u.month.unique())

results = []


def compare(name, sql_df, py_df, keys, cols):
    m = sql_df.merge(py_df, on=keys, suffixes=("_sql", "_py"), how="outer", indicator=True)
    n = len(m)
    ok = int((m["_merge"] == "both").sum())
    maxdiff = 0.0
    match = pd.Series(m["_merge"] == "both")
    for c in cols:
        a, b = m[c + "_sql"].astype(float), m[c + "_py"].astype(float)
        same = (a.isna() & b.isna()) | ((a - b).abs() < 1e-8)
        match &= same
        d = (a - b).abs().dropna()
        if len(d):
            maxdiff = max(maxdiff, float(d.max()))
    results.append(dict(pemeriksaan=name, dibandingkan=n, cocok=int(match.sum()), selisih_maks=round(maxdiff, 12),
                        hasil="cocok" if int(match.sum()) == n else "beda"))


# 1. NG rate per supplier dan per supplier x material
py = u.groupby("supplier_code").agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum"), lots=("lot_code", "nunique")).reset_index()
py["ng_rate"] = py.ng / py.units
compare("NG rate per supplier (Q1)", pd.read_csv(C.RES2 / "ng_supplier.csv"), py, ["supplier_code"], ["units", "ng", "lots", "ng_rate"])
py = u.groupby(["supplier_code", "material_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum"), lots=("lot_code", "nunique")).reset_index()
py["ng_rate"] = py.ng / py.units
compare("NG rate per supplier x material (Q1)", pd.read_csv(C.RES2 / "ng_supplier_material.csv"), py, ["supplier_code", "material_code"], ["units", "ng", "lots", "ng_rate"])

# 2. bulanan, ranking
spine = pd.MultiIndex.from_product([months, suppliers], names=["month", "supplier_code"]).to_frame(index=False)
mo = spine.merge(u.groupby(["month", "supplier_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum"),
                                                          lots=("lot_code", "nunique")).reset_index(), how="left").fillna(0)
mo["ng_rate"] = np.where(mo.units > 0, mo.ng / mo.units.replace(0, np.nan), np.nan)
mo = mo.sort_values(["month", "ng_rate", "supplier_code"], ascending=[True, False, True]).reset_index(drop=True)
mo["rank_ng"] = mo.groupby("month").cumcount() + 1
mo["dense_rank_ng"] = mo.groupby("month")["ng_rate"].transform(lambda s: s.round(4).rank(method="dense", ascending=False))
mo = mo.sort_values(["supplier_code", "month"])
mo["prev_ng_rate"] = mo.groupby("supplier_code").ng_rate.shift(1)
compare("NG rate bulanan, RANK, DENSE_RANK, LAG (Q3)", pd.read_csv(C.RES2 / "ng_month.csv"), mo, ["month", "supplier_code"],
        ["units", "ng", "lots", "ng_rate", "rank_ng", "dense_rank_ng", "prev_ng_rate"])

# 3. rolling 4 minggu
weeks = pd.date_range(u.week_start.min(), u.week_start.max(), freq="7D")
sp = pd.MultiIndex.from_product([weeks, suppliers], names=["week_start", "supplier_code"]).to_frame(index=False)
wk = sp.merge(u.groupby(["week_start", "supplier_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index(), how="left").fillna(0)
wk = wk.sort_values(["supplier_code", "week_start"]).reset_index(drop=True)
g = wk.groupby("supplier_code")
wk["units_4w"] = g.units.transform(lambda s: s.rolling(C.ROLL_WEEKS, min_periods=1).sum())
wk["ng_4w"] = g.ng.transform(lambda s: s.rolling(C.ROLL_WEEKS, min_periods=1).sum())
wk["rolling_ng_rate"] = np.where(wk.units_4w > 0, wk.ng_4w / wk.units_4w.replace(0, np.nan), np.nan)
wk["change_vs_4w_before"] = wk.groupby("supplier_code").rolling_ng_rate.diff(C.ROLL_WEEKS)
sq = pd.read_csv(C.RES2 / "rolling_weekly.csv", parse_dates=["week_start"])
compare("rolling NG rate 4 minggu dan LAG (Q6)", sq, wk, ["week_start", "supplier_code"],
        ["units", "ng", "units_4w", "ng_4w", "rolling_ng_rate", "change_vs_4w_before"])

# 4. per lot, CV antar lot
lt = u.groupby(["lot_code", "supplier_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index()
lt["ng_rate"] = lt.ng / lt.units
compare("NG rate per lot (Q4)", pd.read_csv(C.RES2 / "lot_level.csv")[["lot_code", "supplier_code", "units", "ng", "ng_rate"]], lt,
        ["lot_code", "supplier_code"], ["units", "ng", "ng_rate"])
cv = lt[lt.units >= C.LOT_MIN_UNITS].groupby("supplier_code").ng_rate.agg(lots_eval="count", mean_lot_ng_rate="mean", sd_lot_ng_rate="std").reset_index()
cv["lot_cv"] = cv.sd_lot_ng_rate / cv.mean_lot_ng_rate
compare("koefisien variasi antar lot (Q4)", pd.read_csv(C.RES2 / "lot_cv.csv"), cv, ["supplier_code"],
        ["lots_eval", "mean_lot_ng_rate", "sd_lot_ng_rate", "lot_cv"])

# 5. komponen scorecard
lm = u.groupby(["month", "lot_code", "supplier_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index()
lm["ng_rate"] = lm.ng / lm.units
c2 = lm[lm.units >= C.LOT_MIN_UNITS].groupby(["month", "supplier_code"]).ng_rate.agg(lots_eval="count", mean="mean", sd="std").reset_index()
c2["lot_cv"] = c2.sd / c2["mean"]
comp = mo.sort_values(["supplier_code", "month"]).copy()
g = comp.groupby("supplier_code")
comp["prior_units"] = g.units.transform(lambda s: s.shift(1).rolling(3, min_periods=1).sum())
comp["prior_ng"] = g.ng.transform(lambda s: s.shift(1).rolling(3, min_periods=1).sum())
comp["prior_months"] = g.units.transform(lambda s: s.shift(1).rolling(3, min_periods=1).count()).fillna(0)
comp["prior_ng_rate"] = comp.prior_ng / comp.prior_units
comp["trend_rel"] = (comp.ng_rate - comp.prior_ng_rate) / comp.prior_ng_rate
comp = comp.merge(c2[["month", "supplier_code", "lots_eval", "lot_cv"]], on=["month", "supplier_code"], how="left")
sc = pd.read_csv(C.RES2 / "score_components.csv")
compare("komponen scorecard: CV antar lot dan tren (Q10)", sc, comp[["month", "supplier_code", "ng_rate", "lots_eval", "lot_cv", "prior_months", "prior_ng_rate", "trend_rel"]],
        ["month", "supplier_code"], ["ng_rate", "lots_eval", "lot_cv", "prior_months", "prior_ng_rate", "trend_rel"])

out = pd.DataFrame(results)
out.to_csv(C.RES2 / "crosscheck_sql_pandas.csv", index=False)
print(out.to_string(index=False))
assert (out.hasil == "cocok").all(), "SQL dan pandas tidak cocok"

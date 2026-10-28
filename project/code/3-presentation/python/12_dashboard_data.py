"""12: Data untuk dashboard Streamlit (results/3-presentation). Semua angka berasal dari results/2-analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
import common as CM

R2, R3 = CM.RES2, CM.RES3
sc = pd.read_csv(R2 / "scorecard_monthly.csv")
sc.round(8).to_csv(R3 / "dashboard_scorecard.csv", index=False)
pd.read_csv(R2 / "rolling_weekly.csv")[["week_start", "supplier_code", "units_4w", "ng_4w", "rolling_ng_rate"]].round(8).to_csv(R3 / "dashboard_rolling.csv", index=False)
lots = pd.read_csv(R2 / "lot_level.csv")
pb = pd.read_csv(R2 / "q4_lot_variation.csv")[["supplier_code"]].merge(
    lots.groupby("supplier_code").apply(lambda d: d.ng.sum() / d.units.sum(), include_groups=False).rename("p_bar").reset_index())
lp = lots[lots.units >= CM.LOT_MIN_UNITS].merge(pb, on="supplier_code")
lp["ucl"] = lp.p_bar + 3 * ((lp.p_bar * (1 - lp.p_bar) / lp.units) ** 0.5)
lp["di_atas_ucl"] = (lp.ng_rate > lp.ucl).astype(int)
lp.sort_values(["supplier_code", "first_use", "lot_code"])[["lot_code", "supplier_code", "material_code", "first_use", "units", "ng", "ng_rate", "p_bar", "ucl", "di_atas_ucl"]].round(8).to_csv(R3 / "dashboard_lot.csv", index=False)
u = pd.read_csv(R2 / "usage_detail.csv")
u.groupby(["month", "supplier_code", "material_code", "model_code", "station_code"]).agg(units=("input_qty", "sum"), ng=("ng_material_qty", "sum")).reset_index().to_csv(R3 / "dashboard_cross.csv", index=False)
pd.read_csv(R2 / "hypotheses.csv")[["id", "hipotesis_rancangan", "verdict", "bukti"]].to_csv(R3 / "dashboard_hipotesis.csv", index=False)
pd.read_csv(R2 / "sensitivity_weights.csv").round(8).to_csv(R3 / "dashboard_sensitivitas.csv", index=False)
pd.read_csv(R2 / "impact_scenarios.csv").to_csv(R3 / "dashboard_dampak.csv", index=False, float_format="%.10g")
print("dashboard data ditulis:", len(list(R3.glob("dashboard_*.csv"))), "file")

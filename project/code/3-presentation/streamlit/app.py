"""Dashboard Supplier Quality Scorecard (Streamlit + Plotly). 3 halaman: Scorecard, Detail Supplier, Metodologi.
Data dibaca dari results/3-presentation (dibuat oleh 12_dashboard_data.py). Data simulasi dianonimkan.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results" / "3-presentation"
COL = {"hijau": "#188038", "kuning": "#F9AB00", "merah": "#D93025", "belum dinilai": "#9AA0A6"}


@st.cache_data
def load(name):
    return pd.read_csv(RES / name)


sc, roll, lot = load("dashboard_scorecard.csv"), load("dashboard_rolling.csv"), load("dashboard_lot.csv")
cross, hyp, sens, imp = load("dashboard_cross.csv"), load("dashboard_hipotesis.csv"), load("dashboard_sensitivitas.csv"), load("dashboard_dampak.csv")
months = sorted(sc.month.unique())

st.set_page_config(page_title="Supplier Quality Scorecard", layout="wide")
st.title("Supplier Quality Scorecard")
st.caption("Data simulasi yang dianonimkan. Angka menggambarkan simulasi, bukan kondisi pabrik.")
page = st.sidebar.radio("Halaman", ["Scorecard", "Detail Supplier", "Metodologi"])

if page == "Scorecard":
    month = st.selectbox("Bulan", months, index=len(months) - 1)
    d = sc[sc.month == month].sort_values("supplier_code")
    cols = st.columns(len(d))
    for c, r in zip(cols, d.itertuples()):
        score = "belum dinilai" if pd.isna(r.score) else f"{r.score:.0f}"
        c.metric(r.supplier_code, score, r.status, delta_color="off")
    fig = go.Figure(go.Bar(x=d.supplier_code, y=d.ng_rate * 100, marker_color=[COL[s] for s in d.status],
                           error_y=dict(type="data", symmetric=False, array=(d.ci_high - d.ng_rate) * 100, arrayminus=(d.ng_rate - d.ci_low) * 100)))
    fig.update_layout(yaxis_title="NG rate (%) dengan CI Wilson 95%", height=380)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(d[["supplier_code", "units", "lots", "ng_rate", "lot_cv", "trend", "s_ng", "s_cons", "s_trend", "score", "status"]],
                 hide_index=True, width="stretch")
    st.caption("Supplier dengan kurang dari 2.000 unit atau 10 lot belum diberi status.")

elif page == "Detail Supplier":
    sup = st.selectbox("Supplier", sorted(sc.supplier_code.unique()))
    mats = ["semua"] + sorted(cross.material_code.unique())
    mat = st.selectbox("Jenis material", mats)
    r = roll[roll.supplier_code == sup]
    fig = go.Figure(go.Scatter(x=r.week_start, y=r.rolling_ng_rate * 100, mode="lines", name="rolling 4 minggu"))
    fig.update_layout(yaxis_title="NG rate rolling 4 minggu (%)", height=340)
    st.plotly_chart(fig, width="stretch")
    lt = lot[lot.supplier_code == sup]
    if mat != "semua":
        lt = lt[lt.material_code == mat]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=lt.first_use, y=lt.ng_rate * 100, mode="markers", name="lot",
                              marker=dict(color=["#D93025" if v else "#1A73E8" for v in lt.di_atas_ucl])))
    if len(lt):
        fig2.add_hline(y=float(lt.p_bar.iloc[0]) * 100, line_dash="dash", annotation_text="NG rate rata-rata")
    fig2.update_layout(yaxis_title="NG rate lot (%)", height=340)
    st.plotly_chart(fig2, width="stretch")
    st.caption(f"{int(lt.di_atas_ucl.sum())} lot di atas batas kendali p-chart (merah) dari {len(lt)} lot yang dinilai.")
    cr = cross[cross.supplier_code == sup]
    if mat != "semua":
        cr = cr[cr.material_code == mat]
    c1, c2 = st.columns(2)
    for c, dim in ((c1, "model_code"), (c2, "station_code")):
        g = cr.groupby(dim).agg(units=("units", "sum"), ng=("ng", "sum")).reset_index()
        g["ng_rate"] = g.ng / g.units
        c.write(f"NG rate per {'model' if dim == 'model_code' else 'stasiun'}")
        c.dataframe(g, hide_index=True, width="stretch")

else:
    st.subheader("Definisi skor")
    st.markdown("Skor = 50% NG rate + 25% konsistensi antar lot + 25% tren (bobot awal rancangan). Hijau 80 atau lebih, kuning 60 sampai 79, merah di bawah 60. "
                "Batas skala sub-skor adalah asumsi project (lihat docs/scorecard_definition.md).")
    wt = st.slider("Bobot NG rate (%)", 20, 80, 50, step=10)
    s = sens[(sens.sasaran == "bulan terakhir") & (sens.bobot_ng == wt / 100)]
    st.dataframe(s[["supplier_code", "skor", "ranking", "status"]], hide_index=True, width="stretch")
    st.subheader("Hipotesis")
    st.dataframe(hyp[["id", "verdict", "bukti"]], hide_index=True, width="stretch")
    st.subheader("Dampak (estimated)")
    st.dataframe(imp[["skenario", "ng_terhindari_per_bulan", "ci_low", "ci_high"]], hide_index=True, width="stretch")

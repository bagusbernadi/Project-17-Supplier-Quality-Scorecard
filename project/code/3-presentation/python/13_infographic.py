"""13: One-sheet infografik (PNG dan PDF). Semua angka dibaca dari results/2-analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import common as CM

R = CM.RES2
lat = pd.read_csv(R / "scorecard_latest.csv").sort_values("supplier_code")
imp = pd.read_csv(R / "impact_scenarios.csv").iloc[0]
hy = pd.read_csv(R / "hypotheses.csv").set_index("id")
sup = pd.read_csv(R / "ng_supplier.csv").set_index("supplier_code")
red = pd.read_csv(R / "red_support.csv")
q6 = pd.read_csv(R / "q6_worsening.csv")
worst = imp.supplier
worsening = ", ".join(q6[q6.memburuk == 1].supplier_code)
month = lat.month.iloc[0]
COL = {"hijau": "#188038", "kuning": "#F9AB00", "merah": "#D93025", "belum dinilai": "#9AA0A6"}

fig = plt.figure(figsize=(8.27, 11.69))
fig.text(0.5, 0.95, "Supplier mana yang perlu diaudit lebih dulu?", ha="center", fontsize=20, weight="bold", color="#174EA6")
fig.text(0.5, 0.92, f"Project 17: Supplier Quality Scorecard, status bulan {month} (data simulasi, anonim)", ha="center", fontsize=11, color="#5F6368")
for i, r in enumerate(lat.itertuples()):
    x = 0.05 + i * 0.1875
    fig.patches.append(plt.Rectangle((x, 0.72), 0.17, 0.15, transform=fig.transFigure, facecolor=COL[r.status], edgecolor="none"))
    fig.text(x + 0.085, 0.84, r.supplier_code, ha="center", fontsize=13, weight="bold", color="white")
    fig.text(x + 0.085, 0.795, "-" if pd.isna(r.score) else f"{r.score:.0f}", ha="center", fontsize=24, weight="bold", color="white")
    fig.text(x + 0.085, 0.745, r.status, ha="center", fontsize=11, color="white")
ax = fig.add_axes([0.12, 0.45, 0.78, 0.22])
ax.bar(sup.index, sup.ng_rate * 100, color=["#D93025" if s in set(red.supplier_code) else "#1A73E8" for s in sup.index])
ax.set_ylabel("NG rate seluruh periode (%)")
ax.set_title("NG rate per supplier (merah = pernah berstatus merah)", loc="left", fontsize=12, color="#174EA6")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
pri = lat[lat.status == "merah"].supplier_code.tolist()
bullets = [
    f"Prioritas audit: {', '.join(pri) if pri else 'tidak ada status merah'} (status merah bulan {month}).",
    f"{worst} punya NG rate tertinggi ({sup.loc[worst, 'ng_rate'] * 100:.1f}%), signifikan lebih tinggi dari supplier lain.",
    f"{worsening or 'Tidak ada supplier'} memburuk dalam 8 minggu terakhir (H3: {hy.loc['H3', 'verdict']}).",
    f"Estimasi: jika {worst} setara supplier lain, sekitar {imp.ng_terhindari_per_bulan:.0f} unit NG per bulan terhindari (estimated).",
    "Supplier bervolume kecil belum diberi status karena data terlalu sedikit.",
    "Batasan: data simulasi; bobot dan batas skor adalah asumsi project.",
]
fig.text(0.10, 0.37, "Temuan utama", fontsize=13, weight="bold", color="#174EA6")
for i, b in enumerate(bullets):
    fig.text(0.10, 0.335 - i * 0.04, f"• {b}", fontsize=10, color="#202124")
fig.text(0.5, 0.03, "Angka: results/2-analysis. Estimasi berlabel estimated.", ha="center", fontsize=8, color="#5F6368")
fig.savefig(CM.OUTPUTS / "infographic.png", dpi=150)
fig.savefig(CM.OUTPUTS / "infographic.pdf", metadata={"CreationDate": None, "ModDate": None})
print("infografik ditulis")

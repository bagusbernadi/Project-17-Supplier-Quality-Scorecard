"""14: Rapor supplier (PDF, satu halaman per supplier) untuk bulan penilaian terakhir. Angka dari results/2-analysis."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import common as CM

R = CM.RES2
sc = pd.read_csv(R / "scorecard_monthly.csv")
roll = pd.read_csv(R / "rolling_weekly.csv")
lots = pd.read_csv(R / "q4_pchart_lots.csv")
lat = pd.read_csv(R / "scorecard_latest.csv")
month = lat.month.iloc[0]
COL = {"hijau": colors.HexColor("#188038"), "kuning": colors.HexColor("#F9AB00"), "merah": colors.HexColor("#D93025"), "belum dinilai": colors.HexColor("#9AA0A6")}
ss = getSampleStyleSheet()
doc = SimpleDocTemplate(str(CM.OUTPUTS / f"supplier_report_{month}.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=1.8 * cm, bottomMargin=1.8 * cm, invariant=1)
story = []
for s in sorted(lat.supplier_code):
    row = lat[lat.supplier_code == s].iloc[0]
    story += [Paragraph(f"Rapor supplier {s}: bulan {month}", ss["Title"]),
              Paragraph("Data simulasi yang dianonimkan. Angka menggambarkan simulasi, bukan kondisi pabrik.", ss["Italic"]), Spacer(1, 0.4 * cm)]
    skor = "belum dinilai (data kurang dari 2.000 unit atau 10 lot)" if pd.isna(row.score) else f"{row.score:.0f}"
    t = Table([["Status", row.status], ["Skor", skor], ["NG rate bulan ini", f"{row.ng_rate * 100:.2f}% (CI 95% {row.ci_low * 100:.2f}% sampai {row.ci_high * 100:.2f}%)"],
               ["Unit dan lot", f"{int(row.units)} unit, {int(row.lots)} lot"], ["Skor rata-rata bulan dinilai", "-" if pd.isna(row.skor_rata_rata_bulan) else f"{row.skor_rata_rata_bulan:.0f}"],
               ["Bulan berstatus merah", f"{int(row.bulan_merah)} dari {int(row.bulan_dinilai)} bulan dinilai"]],
              colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (1, 0), (1, 0), COL[row.status]), ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DADCE0")), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    story += [t, Spacer(1, 0.4 * cm)]
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    r = roll[roll.supplier_code == s]
    ax.plot(pd.to_datetime(r.week_start), r.rolling_ng_rate * 100, color="#1A73E8")
    ax.set_ylabel("NG rate rolling 4 minggu (%)"); ax.set_title(f"Tren {s}", loc="left", fontsize=10)
    fig.autofmt_xdate(); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=130); plt.close(fig); buf.seek(0)
    story += [Image(buf, width=16 * cm, height=6.4 * cm), Spacer(1, 0.3 * cm)]
    lt = lots[lots.supplier_code == s].head(5)
    story.append(Paragraph("Lot paling menyimpang (di atas batas kendali p-chart, seluruh periode)", ss["Heading3"]))
    data = [["Lot", "Material", "Unit", "NG", "NG rate"]] + [[r.lot_code, r.material_code, int(r.units), int(r.ng), f"{r.ng_rate * 100:.1f}%"] for r in lt.itertuples()]
    if len(data) == 1:
        data.append(["tidak ada", "", "", "", ""])
    t2 = Table(data, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A73E8")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DADCE0")), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story += [t2, PageBreak()]
doc.build(story[:-1])
print("rapor supplier ditulis")

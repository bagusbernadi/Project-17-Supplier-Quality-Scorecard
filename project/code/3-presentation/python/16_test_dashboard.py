"""16: Uji dashboard dengan Streamlit AppTest: tiap halaman berjalan tanpa exception, angka tampil sama dengan CSV."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from streamlit.testing.v1 import AppTest
import common as CM

APP = CM.ROOT / "code" / "3-presentation" / "streamlit" / "app.py"
sc = pd.read_csv(CM.RES2 / "scorecard_monthly.csv")
last = sorted(sc.month.unique())[-1]
res = {}
at = AppTest.from_file(str(APP), default_timeout=90).run()
res["halaman Scorecard tanpa error"] = not at.exception
d = sc[sc.month == last]
res["jumlah kartu supplier sama dengan CSV"] = len(at.metric) == len(d)
shown = {m.label: m.value for m in at.metric}
res["skor tampil sama dengan CSV"] = all(
    shown[r.supplier_code] == ("belum dinilai" if pd.isna(r.score) else f"{r.score:.0f}") for r in d.itertuples())
at.selectbox[0].set_value(sorted(sc.month.unique())[0]).run()
res["ganti bulan tanpa error"] = not at.exception
for page in ("Detail Supplier", "Metodologi"):
    at.sidebar.radio[0].set_value(page).run()
    res[f"halaman {page} tanpa error"] = not at.exception
    res[f"halaman {page} punya tabel atau grafik"] = len(at.dataframe) + len(at.get("plotly_chart")) >= 1
at.sidebar.radio[0].set_value("Detail Supplier").run()
at.selectbox[0].set_value("SUP-C").run()
at.selectbox[1].set_value("MAT-1").run()
res["filter supplier dan material tanpa error"] = not at.exception
at.sidebar.radio[0].set_value("Metodologi").run()
at.slider[0].set_value(30).run()
res["slider bobot tanpa error"] = not at.exception
out = pd.DataFrame(list(res.items()), columns=["pemeriksaan", "hasil"])
out["hasil"] = out.hasil.map({True: "lulus", False: "gagal"})
out.to_csv(CM.RES3 / "dashboard_test.csv", index=False)
print(out.to_string(index=False))
assert (out.hasil == "lulus").all(), "uji dashboard gagal"

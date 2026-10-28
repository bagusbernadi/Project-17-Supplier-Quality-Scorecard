"""18: README.md dari CSV hasil (angka tidak diketik). Dijalankan paling akhir sebelum build_report.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
import common as CM

R2, R1, R3 = CM.RES2, CM.RES1, CM.RES3
lat = pd.read_csv(R2 / "scorecard_latest.csv")
hy = pd.read_csv(R2 / "hypotheses.csv")
imp = pd.read_csv(R2 / "impact_scenarios.csv").iloc[0]
sup = pd.read_csv(R2 / "ng_supplier.csv").set_index("supplier_code")
gt = pd.read_csv(R2 / "ground_truth_check.csv")
red = pd.read_csv(R2 / "red_support.csv")
q6 = pd.read_csv(R2 / "q6_worsening.csv")
db = pd.read_csv(R1 / "db_tables.csv")
cx = pd.read_csv(R2 / "crosscheck_excel.csv")
py = pd.read_csv(R2 / "crosscheck_sql_pandas.csv")
dt = pd.read_csv(R3 / "dashboard_test.csv")
lk = pd.read_csv(R3 / "leak_scan.csv")


def I(n): return f"{int(round(float(n))):,}".replace(",", ".")
def D(x, d=1): return f"{float(x):.{d}f}".replace(".", ",")
def P(x, d=2): return D(float(x) * 100, d) + "%"


n_lot = int(db.set_index("tabel").loc["material_lot", "baris"]); n_use = int(db.set_index("tabel").loc["lot_usage", "baris"])
last = lat.month.iloc[0]
worst = imp.supplier
worsening = ", ".join(q6[q6.memburuk == 1].supplier_code)
rows = "\n".join(f"| {r.supplier_code} | {I(r.units)} | {P(r.ng_rate)} | {'-' if pd.isna(r.score) else D(r.score, 0)} | {r.status} |" for r in lat.itertuples())
hyp = "\n".join(f"{r.id[1:]}. {r.hipotesis_rancangan} **{r.verdict}.**" for r in hy.itertuples())
txt = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 17: Supplier Quality Scorecard

**Status: Selesai di branch `project-17-build` (belum di-merge ke `main`).** Halaman rancangan dan laporan: [`design-and-report/index.html`](design-and-report/index.html) (tab Design Project dan Report Project).

**Tujuan:** membangun scorecard kualitas supplier dari data OK/NG per lot material yang dianonimkan, untuk menilai supplier mana yang paling sering menyebabkan NG, seberapa konsisten kualitasnya antar lot dan antar waktu, serta apakah perbedaannya signifikan.

| | |
|---|---|
| Kategori | Manufaktur (data anonim) |
| Tingkat | Sedang |
| Data | **Simulasi** yang dianonimkan (karangan; supplier, material, lot, model, stasiun diganti kode; jumlah unit diskala) |
| Tools | DuckDB + SQL (CTE, window function), Python (pandas, SciPy, statsmodels), Excel (dihitung ulang LibreOffice), Streamlit + Plotly |

## 1. Problem

**Pertanyaan utama:** Supplier mana yang paling sering menghasilkan NG, apakah kualitasnya konsisten antar lot dan antar waktu, dan apakah perbedaannya signifikan atau hanya variasi acak?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan). Daftar lengkap ada di halaman rancangan.

## 2. Data

- Data simulasi penerimaan lot dan NG material (100% karangan), dibuat `00_generate_raw.py` lalu dianonimkan `01_anonymize.py`: SUP-A sampai SUP-E, MAT-1 sampai MAT-3, kode lot acak, jumlah unit diskala. Data tidak di-commit; dibuat ulang dari generator dan diverifikasi dengan sidik jari SHA-256 di repo [DataCenter](https://github.com/bagusbernadi/DataCenter/tree/main/simulasi) (`02_verify_fingerprint.py`).
- Versi data v1, seed 17260302 (generator) dan 17260999 (pemetaan kode). Hasil: {I(n_lot)} lot, {I(n_use)} baris pemakaian, Maret sampai 25 Agustus 2026.
- Tabel: `dim_supplier`, `material_lot`, `lot_usage`, `scorecard_monthly`. Kamus data: `project/docs/data_dictionary.md`.

## 3. Analysis

Query window function (RANK, DENSE_RANK, LAG, rolling 4 minggu), CI Wilson, chi-square, uji tingkat lot, regresi logistik, skor tertimbang, dan sensitivitas bobot. Definisi dan asumsi: `project/docs/scorecard_definition.md`.

Scorecard bulan {last} (bobot 50% NG rate, 25% konsistensi antar lot, 25% tren; hijau >= 80, kuning 60 sampai 79, merah < 60):

| Supplier | Unit bulan ini | NG rate | Skor | Status |
|---|---|---|---|---|
{rows}

Hipotesis rancangan:
{hyp}

Uji pemulihan fakta yang ditanam: {int((gt.hasil == 'Sesuai').sum())} dari {len(gt)} pulih penuh (`project/results/2-analysis/ground_truth_check.csv`).

## 4. Recommendation

Audit {', '.join(lat[lat.status == 'merah'].supplier_code)} lebih dulu ({worst} karena NG rate tertinggi, {worsening} karena memburuk). Telusuri lot yang menyimpang sebelum membahas supplier secara keseluruhan. Supplier bervolume kecil belum diberi status sebelum datanya cukup.

## 5. Impact

Estimasi (`estimated`): jika {worst} mencapai NG rate supplier lain, sekitar {I(imp.ng_terhindari_per_bulan)} unit NG per bulan terhindari (CI bootstrap {I(imp.ci_low)} sampai {I(imp.ci_high)}).

```
NG terhindari = (NG rate supplier terburuk - NG rate gabungan supplier lain) x volume bulanan supplier tersebut
```

## Batasan

- **Data adalah simulasi**; angka menggambarkan simulasi, bukan supplier atau lini produksi nyata.
- Batas skala sub-skor, ambang lot, definisi memburuk, dan batas CI adalah asumsi project (label asumsi di `scorecard_definition.md`).
- {int(len(red) - red.didukung.sum())} dari {len(red)} status merah tidak didukung uji NG rate yang signifikan (merah karena konsistensi atau tren).
- Aturan cleaning belum teruji pada data kotor (generator tidak menanam baris kotor).
- Dashboard belum di-deploy (diuji dengan Streamlit AppTest: {int((dt.hasil == 'lulus').sum())} dari {len(dt)} lulus). Success criteria "orang awam menyebut supplier prioritas dalam 1 menit" belum diuji.
- Cek silang: SQL vs pandas {int(py.cocok.sum())} dari {len(py)}, SQL vs Excel {int(cx.cocok.sum())} dari {len(cx)} (Excel dihitung ulang LibreOffice). Pindai kebocoran identitas: {len(lk)} file, {int((lk.hasil == 'gagal').sum())} gagal.

## Menjalankan

Dari folder `project/`:

```
pip install -r requirements.txt
for f in code/1-data-preparation/python/*.py code/2-analysis/python/*.py code/3-presentation/python/*.py; do python3 "$f"; done
python3 ../design-and-report/src/build_report.py
streamlit run code/3-presentation/streamlit/app.py
```

## Struktur repository

```
README.md
index.html                     pengalihan ke design-and-report/
design-and-report/             index.html (tab Design + Report), src/ (page_v1.html, report.css, report_lib.py, build_report.py)
project/
  code/                        common.py; 1-data-preparation/python (00 sampai 04); 2-analysis/{{python,sql}} (05 sampai 11); 3-presentation/{{python,streamlit}} (12 sampai 18)
  results/                     1-data-preparation/ 2-analysis/ 3-presentation/ (CSV hasil, analysis.ipynb)
  outputs/                     crosscheck.xlsx, infographic.pdf dan .png, supplier_report_*.pdf
  data/                        README.md (data tidak di-commit)
  docs/                        scorecard_definition.md, data_dictionary.md, cleaning_decisions.md, simulation_spec.md, datacenter_fingerprint.csv
  requirements.txt
```
"""
(CM.ROOT.parent / "README.md").write_text(txt, encoding="utf-8")
print("README ditulis")

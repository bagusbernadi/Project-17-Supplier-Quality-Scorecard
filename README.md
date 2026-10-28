[← Back to portfolio](https://bagusbernadi.github.io/)

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
- Versi data v1, seed 17260302 (generator) dan 17260999 (pemetaan kode). Hasil: 1.200 lot, 3.584 baris pemakaian, Maret sampai 25 Agustus 2026.
- Tabel: `dim_supplier`, `material_lot`, `lot_usage`, `scorecard_monthly`. Kamus data: `project/docs/data_dictionary.md`.

## 3. Analysis

Query window function (RANK, DENSE_RANK, LAG, rolling 4 minggu), CI Wilson, chi-square, uji tingkat lot, regresi logistik, skor tertimbang, dan sensitivitas bobot. Definisi dan asumsi: `project/docs/scorecard_definition.md`.

Scorecard bulan 2026-08 (bobot 50% NG rate, 25% konsistensi antar lot, 25% tren; hijau >= 80, kuning 60 sampai 79, merah < 60):

| Supplier | Unit bulan ini | NG rate | Skor | Status |
|---|---|---|---|---|
| SUP-A | 10.998 | 3,42% | 33 | merah |
| SUP-B | 1.036 | 0,97% | - | belum dinilai |
| SUP-C | 11.874 | 3,43% | 50 | merah |
| SUP-D | 20.830 | 0,94% | 84 | hijau |
| SUP-E | 18.324 | 1,06% | 80 | hijau |

Hipotesis rancangan:
1. Satu supplier punya NG rate yang lebih tinggi secara signifikan untuk jenis material yang sama. **Terbukti.**
2. Sebagian besar NG suatu supplier berasal dari sedikit lot, bukan merata di semua lot. **Tidak terbukti.**
3. Satu supplier memburuk dalam beberapa bulan terakhir, terlihat dari rolling NG rate. **Terbukti.**
4. Sebagian perbedaan antar supplier hilang setelah model dan stasiun pemakai diperhitungkan. **Terbukti.**
5. Supplier dengan volume kecil punya rentang keyakinan yang terlalu lebar untuk diberi status. **Terbukti.**

Uji pemulihan fakta yang ditanam: 4 dari 5 pulih penuh (`project/results/2-analysis/ground_truth_check.csv`).

## 4. Recommendation

Audit SUP-A, SUP-C lebih dulu (SUP-C karena NG rate tertinggi, SUP-A karena memburuk). Telusuri lot yang menyimpang sebelum membahas supplier secara keseluruhan. Supplier bervolume kecil belum diberi status sebelum datanya cukup.

## 5. Impact

Estimasi (`estimated`): jika SUP-C mencapai NG rate supplier lain, sekitar 444 unit NG per bulan terhindari (CI bootstrap 349 sampai 546).

```
NG terhindari = (NG rate supplier terburuk - NG rate gabungan supplier lain) x volume bulanan supplier tersebut
```

## Batasan

- **Data adalah simulasi**; angka menggambarkan simulasi, bukan supplier atau lini produksi nyata.
- Batas skala sub-skor, ambang lot, definisi memburuk, dan batas CI adalah asumsi project (label asumsi di `scorecard_definition.md`).
- 1 dari 9 status merah tidak didukung uji NG rate yang signifikan (merah karena konsistensi atau tren).
- Aturan cleaning belum teruji pada data kotor (generator tidak menanam baris kotor).
- Dashboard belum di-deploy (diuji dengan Streamlit AppTest: 10 dari 10 lulus). Success criteria "orang awam menyebut supplier prioritas dalam 1 menit" belum diuji.
- Cek silang: SQL vs pandas 1407 dari 7, SQL vs Excel 10 dari 10 (Excel dihitung ulang LibreOffice). Pindai kebocoran identitas: 89 file, 0 gagal.

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
  code/                        common.py; 1-data-preparation/python (00 sampai 04); 2-analysis/{python,sql} (05 sampai 11); 3-presentation/{python,streamlit} (12 sampai 18)
  results/                     1-data-preparation/ 2-analysis/ 3-presentation/ (CSV hasil, analysis.ipynb)
  outputs/                     crosscheck.xlsx, infographic.pdf dan .png, supplier_report_*.pdf
  data/                        README.md (data tidak di-commit)
  docs/                        scorecard_definition.md, data_dictionary.md, cleaning_decisions.md, simulation_spec.md, datacenter_fingerprint.csv
  requirements.txt
```

[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 17: Supplier Quality Scorecard

**Status: Design (rancangan).** Halaman rancangan ada di [`index.html`](index.html). Analisis, dashboard, dan angka hasil belum dikerjakan, sehingga bagian Analysis, Recommendation, dan Impact di bawah masih kosong.

**Tujuan:** membangun scorecard kualitas supplier dari data OK/NG per lot material yang dianonimkan, untuk menilai supplier mana yang paling sering menyebabkan NG, seberapa konsisten kualitasnya antar lot dan antar waktu, serta apakah perbedaannya signifikan.

| | |
|---|---|
| Kategori | Manufaktur (data anonim) |
| Tingkat | Sedang |
| Data | Simulasi yang dianonimkan (data karangan dari generator; supplier, material, lot, model, dan stasiun diganti kode; jumlah unit diskala) |
| Tools | DuckDB + SQL (CTE, window function), Python (pandas, SciPy), Excel, Streamlit + Plotly |

## 1. Problem

**Pertanyaan utama:** Supplier mana yang paling sering menghasilkan NG, apakah kualitasnya konsisten antar lot dan antar waktu, dan apakah perbedaannya signifikan atau hanya variasi acak?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan) dalam tema NG rate, konsistensi, tren, konteks, scorecard, dampak, dan validitas. Daftar lengkap ada di bagian 2 halaman rancangan.

## 2. Data

- Data simulasi penerimaan lot dan NG material (100% karangan, tidak memakai data perusahaan). `scripts/generate_raw.py` membuat data bernama, lalu `scripts/anonymize.py` menggantinya dengan kode: SUP-A sampai SUP-E, MAT-1 sampai MAT-3, kode lot acak, jumlah unit diskala. Data sebelum anonymization dan tabel pemetaan kode ada di `data/private/` dan tidak di-commit.
- Versi data: v1. Tanggal dibuat: 28 Okt 2026. Seed: 17260302 (generator), 17260999 (pemetaan kode). Generator: `scripts/generate_raw.py lalu scripts/anonymize.py`. Hasil v1: 1.200 lot, 3.584 baris pemakaian.
- Ukuran (perkiraan): 5 supplier, 3 jenis material, ±6 bulan, ±1.200 lot.
- Rencana tabel: `dim_supplier`, `material_lot`, `lot_usage`, `scorecard_monthly`.

## 3. Analysis

Belum dikerjakan. Rencana langkah (12 langkah, tahap A sampai D) ada di bagian 6 halaman rancangan: NG rate dengan rentang keyakinan Wilson, RANK()/DENSE_RANK(), rolling 4 minggu dan LAG(), uji chi-square, skor tertimbang, dan analisis sensitivitas bobot.

Hipotesis yang akan diuji (belum terbukti):
1. Satu supplier punya NG rate lebih tinggi secara signifikan.
2. Sebagian besar NG berasal dari sedikit lot.
3. Satu supplier memburuk dalam beberapa bulan terakhir.
4. Sebagian perbedaan hilang setelah model dan stasiun diperhitungkan.
5. Supplier volume kecil belum bisa diberi status.

## 4. Recommendation

Belum dikerjakan. Output yang direncanakan: daftar prioritas audit supplier dan rapor supplier bulanan.

## 5. Impact

Belum dikerjakan. Rumus yang akan dipakai (semua hasil diberi label `estimated`):

```
NG terhindari = (NG rate supplier terburuk − rata-rata supplier lain) × volume supplier tersebut
```

Definisi skor (usulan awal): skor = 50% sub-skor NG rate + 25% konsistensi antar lot + 25% tren; hijau ≥ 80, kuning 60–79, merah < 60. Alasan bobot dan hasil sensitivitas akan ditulis di sini.

## Batasan yang sudah diketahui

- Bergantung pada ketepatan kategori "NG karena material".
- Bobot skor bersifat subjektif.
- Pola belum tentu penyebab.
- Data simulasi: pola supplier dan lot ditanam oleh generator, sehingga hasil membuktikan metode bekerja, bukan kondisi pabrik.

## Struktur repository

```
index.html   Halaman rancangan project (bisa dibuka di browser atau lewat GitHub Pages)
README.md    Dokumen ini
```

Folder `docs/`, `data/anon/`, `scripts/`, `sql/`, `notebooks/`, `dashboard/`, dan `outputs/` ditambahkan saat pengerjaan dimulai. Folder `data/private/` tidak pernah di-commit.

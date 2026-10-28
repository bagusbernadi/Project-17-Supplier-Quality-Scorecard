# Data

Semua data di project ini simulasi (karangan), dibuat oleh generator dengan seed tetap. Tidak ada dataset publik atau data perusahaan, jadi tidak ada masalah lisensi.

| | |
|---|---|
| Versi data | v1 |
| Tanggal dibuat | 28 Okt 2026 |
| Seed | 17260302 (generator), 17260999 (pemetaan kode) |
| Cara membuat ulang | `python3 scripts/generate_raw.py && python3 scripts/anonymize.py` (dari folder project) |
| Hasil v1 | 1.200 lot, 3.584 baris pemakaian |

Isi folder ini tidak di-commit (lihat `.gitignore`). Jejak pembuatan (seed, commit, SHA-256 hasil) dicatat di repo `DataCenter`, folder `simulasi/`. Jika generator, seed, atau versi library berubah, hasil berubah dan versi data harus dinaikkan.

# Data

Semua data di project ini simulasi (karangan), dibuat oleh generator dengan seed tetap. Tidak ada dataset publik atau data perusahaan, jadi tidak ada masalah lisensi.

| | |
|---|---|
| Versi data | v1 |
| Tanggal dibuat | 28 Okt 2026 |
| Seed | 17260302 (generator), 17260999 (pemetaan kode) |
| Cara membuat ulang | `python code/1-data-preparation/python/00_generate_raw.py` lalu `01_anonymize.py` (dari folder `project/`) |
| Hasil v1 | 1.200 lot, 3.584 baris pemakaian |
| Jejak pembuatan | [DataCenter/simulasi](https://github.com/bagusbernadi/DataCenter/tree/main/simulasi) (SHA-256 per file di `simulasi/fingerprints/project-17.sha256`) |

Isi folder ini tidak di-commit (lihat `.gitignore`). Skrip `02_verify_fingerprint.py` mencocokkan hasil generator dengan sidik jari di repo DataCenter (daftar di `docs/datacenter_fingerprint.csv`). Jika generator, seed, atau versi library berubah, hasil berubah dan versi data harus dinaikkan.

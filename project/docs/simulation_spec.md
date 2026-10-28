# Spesifikasi simulasi (Project 17)

Data adalah simulasi. Parameter ada di `code/1-data-preparation/python/00_generate_raw.py` (seed 17260302, versi v1) dan identik dengan generator di repo DataCenter (sidik jari SHA-256 dicek oleh `02_verify_fingerprint.py`).

| Parameter | Nilai |
|---|---|
| Periode | 130 hari kerja, mulai 2026-03-02 |
| Lot | 1.200; ukuran 800 sampai 6.000 unit sebelum skala |
| Supplier (bobot volume, pengali NG) | lima supplier dengan pengali 1,00 / 0,95 / 1,05 / 2,30 / 1,10; bobot 0,30 / 0,27 / 0,20 / 0,20 / 0,03 (kode asli diacak saat anonimisasi) |
| NG dasar | 0,8% |
| Faktor model | M-1 0,8; M-2 1,0; M-3 1,6 (pada kode asli; kode diacak oleh anonimisasi) |
| Lot buruk | 8% lot, NG 6 kali |
| Supplier memburuk | satu supplier, mulai hari ke-90 (2026-07-06), NG 2,2 kali |
| Supplier terburuk | 60% pemakaiannya di model terberat |
| Hasil penerimaan | Pass 94%, sisanya Conditional atau Reject |

Fakta yang ditanam (5): supplier dengan NG tertinggi, sedikit lot menyumbang banyak NG, satu supplier memburuk sejak 2026-07-06, model terberat menjelaskan sebagian selisih, supplier volume kecil. Hasil uji pemulihan: `results/2-analysis/ground_truth_check.csv` (hanya `11_ground_truth_check.py` yang membaca `ground_truth.json`).

**Sifat simulasi yang dicatat jujur.** Tidak ada baris kotor yang ditanam. Hasil bulan Agustus berhenti pada 25 Agustus 2026, jadi bulan itu tidak lengkap. Faktor skala unit membuat jumlah mutlak berbeda dari generator, persentase hampir sama.

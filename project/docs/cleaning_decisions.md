# Keputusan pembersihan data (Project 17, Q13)

`03_clean.py` memeriksa delapan aturan. Pelanggaran dicatat di `results/1-data-preparation/cleaning_log.csv`, jumlahnya di `data_quality.csv`.

| # | Aturan | Keputusan | Hasil pada data v1 |
|---|---|---|---|
| 1 | Lot tanpa supplier atau material | lot dibuang | 0 |
| 2 | Pemakaian tanpa lot di tabel lot | baris dibuang dari analisis | 0 |
| 3 | Lot ganda (kode sama) | baris pertama dipakai | 0 |
| 4 | Baris pemakaian ganda | baris pertama dipakai | 0 |
| 5 | NG lebih besar dari input | baris dibuang | 0 |
| 6 | Input tidak positif | baris dibuang | 0 |
| 7 | Pemakaian sebelum lot diterima | baris dibuang | 0 |
| 8 | Pasangan supplier-material tidak ada di dim_supplier | lot dibuang | 0 |

Aturan 1 sampai 4 berasal dari rancangan (lot tanpa supplier, NG tanpa lot, duplikat). Aturan 5 sampai 8 ditambahkan project ini [asumsi].

**Informasi, bukan pelanggaran.** Lot berhasil Reject saat penerimaan tetapi tetap dipakai: dipakai di analisis dan dihitung di `data_quality.csv`.

**Catatan jujur.** Generator tidak menanam baris kotor, sehingga tidak ada aturan yang pernah terpicu pada data ini. Aturan pembersihan belum teruji pada data kotor; ini item terbuka (lihat Report 7.6).

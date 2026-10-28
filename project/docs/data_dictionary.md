# Kamus data (Project 17)

Empat tabel di `supplier.duckdb` (tidak di-commit). Tiga tabel dimuat dari `data/clean/`, satu dihitung oleh `09_scorecard.py`.

```
dim_supplier 1 --- * material_lot 1 --- * lot_usage        scorecard_monthly (hasil, satu baris per supplier per bulan)
 (supplier_code, material_code)   (lot_code)
```

| Tabel | Kolom | Arti |
|---|---|---|
| dim_supplier | supplier_code, material_code, active_from | pasangan supplier dan material yang dipasok, tanggal lot pertama |
| material_lot | lot_code, supplier_code, material_code, receive_date, lot_qty, incoming_result | satu lot yang diterima; hasil penerimaan Pass, Conditional, atau Reject |
| lot_usage | date, lot_code, station_code, model_code, input_qty, ng_material_qty | pemakaian satu lot di satu stasiun, satu model, satu hari; NG karena material |
| scorecard_monthly | month, supplier_code, units, lots, ng, ng_rate, ci_low, ci_high, lots_eval, lot_cv, trend, s_ng, s_cons, s_trend, score, status | skor satu supplier untuk satu bulan |

## Aturan anonimisasi (01_anonymize.py)
| Kolom asli | Perlakuan |
|---|---|
| nama supplier | kode SUP-A sampai SUP-E (urutan acak, seed 17260999) |
| nama material | MAT-1 sampai MAT-3 |
| nama stasiun, nama produk | ST-A sampai ST-E, M-1 sampai M-3 |
| kode lot | L- diikuti 4 digit heksadesimal acak |
| jumlah unit (lot_qty, input_qty, ng_material_qty) | dikalikan faktor skala rahasia dan dibulatkan; persentase NG kurang lebih tetap |
| tabel pemetaan dan faktor skala | `data/mapping_key.json`, tidak di-commit |

Pengecekan: `01_anonymize.py` gagal bila ada nama asli di berkas anonim; `17_scan_leak.py` memindai semua file yang akan di-commit (hasil: `results/3-presentation/leak_scan.csv`).

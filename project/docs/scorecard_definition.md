# Definisi scorecard dan kriteria keputusan (Project 17)

Dokumen ini ditulis sebelum hasil uji dilihat. Nilai ada di `code/common.py`. Label **[rancangan]** = ditetapkan Design Project, **[asumsi]** = ditetapkan di project ini karena rancangan tidak menentukannya (diuji sensitivitasnya di bagian 5).

## 1. Skor dan status
- Skor = 50% sub-skor NG rate + 25% sub-skor konsistensi + 25% sub-skor tren **[rancangan: bobot awal]**.
- Status: skor >= 80 hijau, 60 sampai 79 kuning, < 60 merah **[rancangan]**.
- Belum dinilai: supplier dengan < 2.000 unit atau < 10 lot pada periode penilaian **[rancangan]**. Periode penilaian = satu bulan kalender **[asumsi]**.

## 2. Sub-skor (semua 0 sampai 100, makin tinggi makin baik)
| Sub-skor | Rumus | Label |
|---|---|---|
| NG rate | 100 x max(0, 1 - NG rate / 4%) | [asumsi] NG rate 4% = skor 0 |
| Konsistensi | 100 x max(0, 1 - CV antar lot / 3,0); CV = simpangan baku NG rate lot-bulan / rata-ratanya, lot dengan >= 100 unit | [asumsi] CV 3,0 = skor 0 |
| Tren | 100 x max(0, 1 - max(0, perubahan relatif) / 100%); perubahan relatif = NG rate bulan ini terhadap NG rate gabungan 3 bulan sebelumnya | [asumsi] kenaikan +100% = skor 0; penurunan = skor 100 |

Bulan tanpa data 3 bulan sebelumnya (tren tidak bisa dihitung): skor dihitung dari dua sub-skor lain dengan bobot dinormalkan ulang **[asumsi]**.

## 3. Ukuran lain yang tidak ada di rancangan [asumsi]
- Lot "di atas ambang" (Q5): NG rate lot > 2%; sensitivitas 1,5% dan 3%.
- Lot dinilai (Q4, Q5): terpakai >= 100 unit.
- Memburuk (Q6, H3): 8 minggu terakhir dibanding minggu sebelumnya; rasio >= 1,5 dan uji dua proporsi satu sisi dengan koreksi Holm p < 0,05.
- Rentang Wilson "cukup sempit" (Q9, H5): setengah lebar <= 25% dari NG rate.
- 10% lot teratas dan batas 50% (H2).
- Alfa 0,05 untuk semua uji.

## 4. Kriteria keputusan hipotesis (tetap, sebelum uji)
| H | Terbukti bila | Dasar |
|---|---|---|
| H1 | Pada sedikitnya satu jenis material, supplier tertinggi signifikan lebih tinggi dari semua supplier lain pada material itu, pada uji tingkat unit (dua proporsi, Holm) dan tingkat lot (Mann-Whitney, Holm). Hanya tingkat unit: Belum bisa disimpulkan. | Baris pemakaian satu lot tidak independen, sehingga uji unit cenderung terlalu yakin. |
| H2 | > 50% NG berasal dari 10% lot teratas pada sedikitnya 3 dari 5 supplier. | Pembanding: simulasi semua lot sama. |
| H3 | Sedikitnya satu supplier memenuhi definisi memburuk (bagian 3). | |
| H4 | Model dan stasiun menjelaskan >= 10% selisih log odds ratio supplier dengan NG rate tertinggi (GLM binomial, skala dispersi Pearson). | |
| H5 | Setengah lebar CI Wilson bulanan supplier bervolume terkecil > 25% NG rate pada sedikitnya separuh bulan. | |

## 5. Uji sensitivitas yang dikerjakan
- Bobot (Q11): bobot NG rate 20% sampai 80% (sisa dibagi rata) dan kisi bobot langkah 5% dengan tiap bobot >= 10%.
- Konstanta skala (ambang skor 0 tiap sub-skor): ukuran 0,5x dan 2x.
- Ambang lot (Q5): 1,5%, 2%, 3%.

## 6. Status merah harus didukung uji
Supplier berstatus merah dinyatakan "didukung" bila NG rate bulan itu signifikan lebih tinggi dari gabungan supplier lain (dua proporsi satu sisi, Holm atas supplier merah) dan uji tingkat lot (Mann-Whitney) juga signifikan. Selain itu: "tidak didukung".

## 7. Catatan data bulan terakhir
Data berakhir 25 Agustus 2026, sehingga Agustus tidak lengkap [asumsi: tetap dinilai sebagai periode penilaian terakhir]. Volume bulanan untuk dampak (Q12) memakai rata-rata empat bulan penuh (April sampai Juli).

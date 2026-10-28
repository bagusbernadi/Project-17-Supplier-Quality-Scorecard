"""Generator Report v2 (Project 17). Dijalankan paling akhir, setelah seluruh pipeline dijalankan ulang dari nol.

Input : design-and-report/src/page_v1.html (rancangan, pane Design TIDAK diubah), project/results/*.
Output: design-and-report/index.html
Setiap angka di teks Report berasal dari CSV lewat helper report_lib (I, D, P, cs). audit() memeriksa token angka
yang tidak berasal dari data dan tidak ada di STATIC. ground_truth.json tidak dibaca di sini (hanya hasil cek 11).
"""
import re
import sys
from html import escape as esc
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = REPO / "project"
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(HERE))
import pandas as pd
import common as C
import report_lib as R
from report_lib import I, D, P, cs, pill, BLUE, GREY, table, qa, legend, bars, lines, audit

SRC = (HERE / "page_v1.html").read_text(encoding="utf-8")
CSS_EXTRA = (HERE / "report.css").read_text(encoding="utf-8")
r1, r2, r3 = C.RES1, C.RES2, C.RES3


def rd(d, n):
    return pd.read_csv(d / n)


q1 = rd(r2, "q1_ng_rate_ci.csv"); q1top = rd(r2, "q1_top_per_material.csv"); q2 = rd(r2, "q2_tests.csv")
q3 = rd(r2, "q3_rank_summary.csv"); q4 = rd(r2, "q4_lot_variation.csv"); q4p = rd(r2, "q4_pchart_lots.csv")
q5 = rd(r2, "q5_lot_threshold.csv"); q6 = rd(r2, "q6_worsening.csv"); q7 = rd(r2, "q7_month_change.csv")
q8 = rd(r2, "q8_adjusted_or.csv"); q8t = rd(r2, "q8_cross_tests.csv"); q9m = rd(r2, "q9_supplier_month_ci.csv")
q9u = rd(r2, "q9_unit_minimum.csv"); conc = rd(r2, "concentration_lots.csv"); hyp = rd(r2, "hypotheses.csv")
nm = rd(r2, "ng_month.csv"); wk = rd(r2, "rolling_weekly.csv"); sup = rd(r2, "ng_supplier.csv").set_index("supplier_code")
sc = rd(r2, "scorecard_monthly.csv"); lat = rd(r2, "scorecard_latest.csv"); red = rd(r2, "red_support.csv")
sw = rd(r2, "sensitivity_weights.csv"); sg = rd(r2, "sensitivity_grid.csv").set_index("sasaran"); ss = rd(r2, "sensitivity_scale.csv")
imp = rd(r2, "impact_scenarios.csv"); gtc = rd(r2, "ground_truth_check.csv"); scx = rd(r2, "scorecard_crosscheck.csv")
cx_py = rd(r2, "crosscheck_sql_pandas.csv"); cx_ex = rd(r2, "crosscheck_excel.csv")
dq = rd(r1, "data_quality.csv").set_index("kategori"); dbc = rd(r1, "db_checks.csv"); dbt = rd(r1, "db_tables.csv")
fp = rd(r1, "fingerprint_check.csv"); dtest = rd(r3, "dashboard_test.csv"); leak = rd(r3, "leak_scan.csv")
usage = rd(r2, "usage_detail.csv")
anon_lot = pd.read_csv(C.ANON / "material_lot.csv"); anon_use = pd.read_csv(C.ANON / "lot_usage.csv")


def pv(p):
    return "< 0,001" if float(p) < 0.001 else D(float(p), 3)


def ci(r, d=2):
    return f"CI 95% {D(r.ci_low * 100, d)}% sampai {D(r.ci_high * 100, d)}%"


H = {r.id: r for r in hyp.itertuples()}
sups = sorted(sup.index)
months = sorted(sc.month.unique())
last = months[-1]
n_months = len(months)
n_lot, n_use = len(anon_lot), len(anon_use)
tot_units = int(usage.input_qty.sum())
tot_ng = int(usage.ng_material_qty.sum())
dqv = {k: int(dq.loc[k, "jumlah"]) for k in dq.index}
n_db_ok = int((dbc.hasil == "lulus").sum())
n_fp_ok = int((fp.hasil == "cocok").sum())
n_py, n_py_ok = len(cx_py), int(cx_py.cocok.sum())
n_ex, n_ex_ok = len(cx_ex), int(cx_ex.cocok.sum())
n_dash, n_dash_ok = len(dtest), int((dtest.hasil == "lulus").sum())
n_leak, n_leak_fail = len(leak), int((leak.hasil == "gagal").sum())
n_sc_ok = int(scx.cocok.sum()); n_sc = int(scx.baris.sum())
worst = imp.iloc[0].supplier
worsening = list(q6[q6.memburuk == 1].supplier_code)
pri = list(lat[lat.status == "merah"].supplier_code)
small = sup.units.idxmin()
q2s = q2.iloc[0]; kw = q2[q2.uji.str.startswith("Kruskal")].iloc[0]
qm = q1[q1.tingkat == "supplier"].set_index("supplier_code")
red_ok = int(red.didukung.sum()); red_n = len(red)
n_gt_ok = int((gtc.hasil == "Sesuai").sum())
imp0 = imp.iloc[0]
rated_months = sc[sc.status != "belum dinilai"]
pct_thr = q5[q5.dasar == 1].set_index("supplier_code")
unmin = q9u.set_index("acuan").unit_minimum
sm_small = q9m[q9m.supplier_code == small]
adj = q8.set_index("supplier_code")
ST = {"hijau": "", "kuning": "p", "merah": "d", "belum dinilai": "d"}


def stpill(s):
    return pill(s, {"hijau": "", "kuning": "p"}.get(s, "d" if s == "merah" else "p"))


def verdict_pill(v):
    return pill(v, {"Terbukti": "", "Belum bisa disimpulkan": "p", "Tidak terbukti": "d"}.get(v, "d"))


def kpi(v, l, d, color):
    return (f'<div class="card kpi" style="--h:var(--{color})"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>')


SUPC = {"SUP-A": "#1A73E8", "SUP-B": "#9AA0A6", "SUP-C": "#D93025", "SUP-D": "#188038", "SUP-E": "#9334E6"}
chart_ng = bars([(s, float(qm.loc[s, "ng_rate"]), SUPC[s], f"{s}: {D(qm.loc[s, 'ng_rate'] * 100, 2)}% ({I(qm.loc[s, 'ng'])} NG dari {I(qm.loc[s, 'units'])} unit)") for s in sups],
                lambda v: D(v * 100, 1) + "%", "Grafik NG rate per supplier", h=250, rot=0)
wkd = sorted(wk.week_start.unique())
chart_roll = lines([w[5:] for w in wkd], [(s, SUPC[s], 2, [float(wk[(wk.supplier_code == s) & (wk.week_start == w)].rolling_ng_rate.iloc[0]) for w in wkd]) for s in sups],
                   lambda v: D(v * 100, 1) + "%", "Grafik rolling NG rate 4 minggu per supplier", h=260, zero=True)
base_w = sw[(sw.sasaran == "bulan terakhir") & (sw.bobot_ng == 0.5)].set_index("supplier_code")
chart_score = bars([(s, float(lat.set_index("supplier_code").loc[s, "score"]) if pd.notna(lat.set_index("supplier_code").loc[s, "score"]) else 0.0,
                     {"hijau": "#188038", "kuning": "#F9AB00", "merah": "#D93025", "belum dinilai": "#9AA0A6"}[lat.set_index("supplier_code").loc[s, "status"]],
                     f"{s}: " + ("belum dinilai" if pd.isna(lat.set_index("supplier_code").loc[s, "score"]) else f"skor {D(lat.set_index('supplier_code').loc[s, 'score'], 0)}"))
                    for s in sups], lambda v: D(v, 0), "Grafik skor scorecard bulan terakhir", h=240, ymax=100, rot=0)

# ---------- pertanyaan ----------
QS = [
    (1, "Supplier mana yang punya NG rate tertinggi untuk tiap jenis material?", "Utama"),
    (2, "Apakah perbedaan NG rate antar supplier signifikan, atau hanya variasi acak?", "Utama"),
    (3, "Bagaimana ranking supplier setiap bulan, dan apakah ranking itu berubah?", "Utama"),
    (4, "Seberapa besar variasi NG rate antar lot untuk tiap supplier, dan lot mana yang menyimpang?", "Utama"),
    (5, "Berapa persen lot tiap supplier yang melewati ambang NG yang disepakati?", "Pendukung"),
    (6, "Bagaimana rolling NG rate 4 minggu tiap supplier, dan siapa yang memburuk?", "Utama"),
    (7, "Apakah perubahan NG rate antar bulan cukup besar untuk dianggap nyata?", "Pendukung"),
    (8, "Apakah NG suatu supplier terkumpul di model atau stasiun tertentu?", "Pendukung"),
    (9, "Berapa jumlah unit minimum agar NG rate supplier bisa dinilai dengan cukup yakin?", "Pendukung"),
    (10, "Berapa skor gabungan dan status hijau, kuning, atau merah setiap supplier?", "Utama"),
    (11, "Apakah urutan supplier tetap sama jika bobot skor diubah?", "Tambahan"),
    (12, "Berapa unit NG terhindari per bulan jika supplier terburuk mencapai rata-rata supplier lain?", "Utama"),
    (13, "Berapa persen data tidak valid (lot tanpa supplier, NG tanpa lot, duplikat), dan bagaimana ditangani?", "Utama"),
    (14, "Apakah NG rate dan ranking dari SQL sama dengan hitungan manual di Excel?", "Utama"),
]
WARN = {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}
tops = q1top.set_index("material_code")
n_top_sig = int(((q1top.p_unit_holm_maks < 0.05) & (q1top.p_lot_holm_maks < 0.05)).sum())
chg = int(q3.perubahan_rank.sum())
ng_sig_months = q7[q7.nyata == 1]
ucl_total = int(q4p.shape[0])
sa = sc[(sc.supplier_code == worsening[0]) & (sc.month == last)].iloc[0] if worsening else None
glob_other = imp0.ng_rate_pembanding
ANS = {
    1: ("NG rate tertinggi per material: " + "; ".join(f"{m} {tops.loc[m, 'supplier_tertinggi']} ({D(tops.loc[m, 'ng_rate'] * 100, 2)}%, CI 95% {D(tops.loc[m, 'ci_low'] * 100, 2)}% sampai {D(tops.loc[m, 'ci_high'] * 100, 2)}%)" for m in sorted(tops.index))
        + f". Secara keseluruhan {worst} tertinggi ({D(qm.loc[worst, 'ng_rate'] * 100, 2)}%, {ci(qm.loc[worst])}). Semua {I(n_top_sig)} supplier tertinggi signifikan pada uji unit dan uji lot (Holm)."),
    2: (f"Ya. Chi-square antar {I(len(sups))} supplier {D(q2s.statistik, 0)}, p {pv(q2s.p_value)}, Cramér's V {D(q2s.effect_size_cramers_v, 3)} (efek kecil). "
        f"Uji tingkat lot (Kruskal-Wallis) p {pv(kw.p_value)}. Chi-square atas unit cenderung terlalu yakin karena baris satu lot tidak independen, sehingga uji lot dipakai sebagai pembanding."),
    3: (f"{worst} peringkat 1 (NG rate tertinggi) pada {I(int(q3.set_index('supplier_code').loc[worst, 'bulan_rank_1']))} dari {I(n_months)} bulan, peringkatnya tidak pernah berubah. "
        f"Peringkat supplier lain berubah {I(int(q3[q3.supplier_code != worst].perubahan_rank.sum()))} kali dari {I(int(q3[q3.supplier_code != worst].jumlah_bulan.sub(1).sum()))} pergantian bulan. "
        f"{small} bervolume kecil, sehingga peringkatnya mudah berubah karena beberapa NG saja."),
    4: (f"Koefisien variasi (CV) NG rate antar lot: " + ", ".join(f"{s} {D(q4.set_index('supplier_code').loc[s, 'lot_cv'], 2)}" for s in sups)
        + f". Variasi jauh di atas variasi binomial murni (dispersi berlebih {D(q4.dispersi_berlebih.min(), 1)} sampai {D(q4.dispersi_berlebih.max(), 1)}). {I(ucl_total)} lot di atas batas p-chart (3 sigma). "
        f"Ukuran lot dinilai (>= {I(C.LOT_MIN_UNITS)} unit) adalah asumsi."),
    5: (f"Persen lot dengan NG rate di atas {D(C.LOT_THRESHOLD * 100, 0)}% (asumsi): " + ", ".join(f"{s} {P(pct_thr.loc[s, 'persen'], 0)} (n {I(pct_thr.loc[s, 'lot_dinilai'])})" for s in sups)
        + f". Ambang {D(C.LOT_THRESHOLD * 100, 0)}% bukan dari rancangan; hasil untuk 1,5% dan 3% ada di results/2-analysis/q5_lot_threshold.csv."),
    6: (f"Supplier memburuk: {', '.join(worsening) or 'tidak ada'}. NG rate 8 minggu terakhir {D(q6.set_index('supplier_code').loc[worsening[0], 'ng_rate_terkini'] * 100, 2)}% dibanding "
        f"{D(q6.set_index('supplier_code').loc[worsening[0], 'ng_rate_sebelumnya'] * 100, 2)}% sebelumnya (rasio {D(q6.set_index('supplier_code').loc[worsening[0], 'rasio'], 2)}, p Holm {pv(q6.set_index('supplier_code').loc[worsening[0], 'p_holm'])}). "
        f"Definisi memburuk (8 minggu, rasio >= 1,5) adalah asumsi."),
    7: (f"{I(len(ng_sig_months))} dari {I(len(q7))} perubahan bulanan nyata setelah koreksi Holm; per supplier: " + ", ".join(f"{s} {I(int(q7[q7.supplier_code == s].nyata.sum()))} dari {I(int((q7.supplier_code == s).sum()))}" for s in sups)
        + f". Bulan {last} tidak lengkap (data sampai 25 Agustus). Perubahan yang nyata tidak otomatis berarti memburuk: arah naik dan turun sama-sama muncul."),
    8: (f"NG rate {worst} lebih tinggi pada model M-2 dan sebagian besar pemakaiannya ada di model itu. Setelah model dan stasiun diperhitungkan, OR {worst} turun dari {D(adj.loc[worst, 'or_tanpa_koreksi'], 2)} menjadi {D(adj.loc[worst, 'or_terkoreksi'], 2)} "
        f"({D(adj.loc[worst, 'persen_selisih_dijelaskan'] * 100, 0)}% selisih log dijelaskan), tetapi {worst} tetap yang tertinggi. Pola ini belum tentu penyebab; pengujian faktor penyebab di luar lingkup."),
    9: (f"Agar setengah lebar CI Wilson <= {D(C.REL_HALFWIDTH_OK * 100, 0)}% dari NG rate, dibutuhkan sekitar {I(unmin['rata-rata semua supplier'])} unit (rata-rata), {I(unmin['supplier terburuk'])} unit (supplier terburuk), "
        f"dan {I(unmin['supplier terbaik'])} unit (supplier terbaik). Batas {I(C.MIN_UNITS)} unit atau {I(C.MIN_LOTS)} lot di rancangan lebih longgar untuk supplier dengan NG rate rendah. Batas 25% adalah asumsi."),
    10: ("Status bulan " + last + ": " + ", ".join(f"{r.supplier_code} {r.status}" + ("" if pd.isna(r.score) else f" ({D(r.score, 0)})") for r in lat.itertuples())
         + f". Status merah didukung uji signifikan pada {I(red_ok)} dari {I(red_n)} kasus bulan-merah. Batas skala sub-skor (NG rate 4%, CV 3,0, tren +100%) adalah asumsi."),
    11: (f"Pada bulan terakhir urutan sama di {P(sg.loc['bulan terakhir', 'urutan_sama_persen'], 0)} dari {I(sg.loc['bulan terakhir', 'kombinasi_bobot'])} kombinasi bobot, tetapi status sebagian supplier berubah. "
         f"Pada rata-rata bulan dinilai urutan sama hanya {P(sg.loc['rata-rata bulan dinilai', 'urutan_sama_persen'], 0)}; supplier teratas sama {P(sg.loc['rata-rata bulan dinilai', 'supplier_teratas_sama_persen'], 0)}, supplier terendah sama {P(sg.loc['rata-rata bulan dinilai', 'supplier_terendah_sama_persen'], 1)}. Urutan bergantung pada bobot, terutama untuk supplier di tengah."),
    12: (f"Estimasi (estimated): jika {worst} setara supplier lain ({D(glob_other * 100, 2)}%), sekitar {I(imp0.ng_terhindari_per_bulan)} unit NG per bulan terhindari (CI bootstrap {I(imp0.ci_low)} sampai {I(imp0.ci_high)}), "
         f"{P(imp0.persen_ng_supplier_terhindari, 0)} dari NG {worst}. Volume bulanan {I(imp0.volume_bulanan)} unit adalah rata-rata empat bulan penuh (asumsi)."),
    13: (f"Pada data v1, {I(dqv['baris pemakaian valid'])} dari {I(dqv['baris pemakaian (mentah)'])} baris valid. Tidak ada lot tanpa supplier, NG tanpa lot, atau duplikat. "
         f"Generator tidak menanam baris kotor, sehingga aturan cleaning belum teruji pada data kotor. {I(dqv['lot dengan hasil Reject saat penerimaan yang tetap dipakai (info)'])} baris dipakai dari lot berhasil Reject (informasi)."),
    14: (f"Ya. Cek silang Excel untuk NG rate dan ranking dua bulan: {I(n_ex_ok)} dari {I(n_ex)} sama dengan SQL. Excel dihitung ulang oleh LibreOffice, bukan dihitung manual. "
         f"Cek SQL vs pandas: {I(n_py_ok)} dari {I(n_py)} pemeriksaan cocok; skor SQL vs pandas {I(n_sc_ok)} dari {I(n_sc)}."),
}


def qchip(n, t):
    return f'<a class="qc{" w" if n in WARN else ""}" href="#sec2{n}" title="{esc(t)}">Q{n}</a>'


def qcard(n, t, p):
    return f'<span id="sec2{n}"></span>' + qa(f"Q{n}", t, p, ANS[n], status="Terjawab" if n not in WARN else "Dengan catatan", warn=n in WARN)


def block(qs):
    return "".join(qcard(n, t, p) for n, t, p in QS if n in qs)


def hyp_row(hid):
    h = H[hid]
    return [f"<b>{hid}</b>", esc(h.hipotesis_rancangan), esc(cs(h.bukti)), verdict_pill(h.verdict), esc(cs(h.catatan_keputusan))]


hyp_table = table(["ID", "Hipotesis (sesuai rancangan)", "Bukti", "Verdict", "Kriteria keputusan"], [hyp_row(x) for x in ["H1", "H2", "H3", "H4", "H5"]])
pivot_rank = nm.pivot(index="month", columns="supplier_code", values="rank_ng")
pivot_score = sc.pivot(index="month", columns="supplier_code", values="score")
pivot_status = sc.pivot(index="month", columns="supplier_code", values="status")

sec2 = []
sec2.append(f'<div class="card"><h3>Jawaban singkat</h3><p>Semua {I(14)} pertanyaan terjawab dengan angka dari data ({I(9)} Utama, {I(4)} Pendukung, {I(1)} Tambahan). '
            f'{I(len(WARN))} di antaranya diberi catatan kuning karena ukuran atau batas ditetapkan sendiri (asumsi), sampel kecil, atau data simulasi. '
            f'Pertanyaan utama project dijawab di bagian 7.</p><p class="how">Klik nomor pertanyaan untuk melompat. Q hijau = terjawab. Q kuning = terjawab dengan catatan.</p>'
            f'<div class="qchips">' + "".join(qchip(n, t) for n, t, _ in QS) + '</div></div>')
sec2.append('<h3>2.1 NG rate: seberapa sering gagal</h3>'
            f'<div class="card"><p>Grafik 2.1a: NG rate per supplier seluruh periode.</p>{chart_ng}'
            f'<p>Tabel 2.1b: NG rate per supplier dan material, dengan CI Wilson 95% dan jumlah data.</p>'
            + table(["Supplier", "Material", "Unit", "NG", "NG rate", "CI 95%", "Lot"],
                    [[r.supplier_code, r.material_code, I(r.units), I(r.ng), P(r.ng_rate, 2), f"{D(r.ci_low * 100, 2)}% sampai {D(r.ci_high * 100, 2)}%", I(r.lots)] for r in q1[q1.tingkat == "supplier x material"].itertuples()])
            + f'<p>Tabel 2.1c: uji antar supplier. Uji unit (chi-square) dan uji lot (Kruskal-Wallis, Mann-Whitney) dipasangkan karena baris dalam satu lot tidak independen.</p>'
            + table(["Uji", "Statistik", "Derajat bebas", "p", "Cramér's V", "n"],
                    [[esc(r.uji), D(r.statistik, 1), I(r.derajat_bebas), pv(r.p_value), ("-" if pd.isna(r.effect_size_cramers_v) else D(r.effect_size_cramers_v, 3)), I(r.n_unit)] for r in q2.itertuples()])
            + '</div>')
sec2.append(block([1, 2]))
sec2.append('<h3>2.2 Ranking bulanan</h3>'
            f'<div class="card"><p>Tabel 2.2a: peringkat NG rate per bulan (1 = tertinggi, RANK()).</p>'
            + table(["Bulan"] + sups, [[m] + [I(pivot_rank.loc[m, s]) for s in sups] for m in months])
            + '</div>')
sec2.append(block([3]))
sec2.append('<h3>2.3 Konsistensi antar lot</h3>'
            f'<div class="card"><p>Tabel 2.3a: variasi NG rate antar lot (lot dengan >= {I(C.LOT_MIN_UNITS)} unit) dan lot di atas batas p-chart.</p>'
            + table(["Supplier", "Lot dinilai", "Rata-rata NG rate lot", "CV antar lot", "Dispersi berlebih", "Lot di atas batas", "Persen"],
                    [[r.supplier_code, I(r.lots_eval), P(r.mean_lot_ng_rate, 2), D(r.lot_cv, 2), D(r.dispersi_berlebih, 1), I(r.lot_di_atas_ucl), P(r.persen_lot_di_atas_ucl, 1)] for r in q4.itertuples()])
            + f'<p>Tabel 2.3b: persen lot di atas ambang {D(C.LOT_THRESHOLD * 100, 0)}% (asumsi), dengan CI Wilson. Sensitivitas ambang ada di q5_lot_threshold.csv.</p>'
            + table(["Supplier", "Lot dinilai", "Di atas ambang", "Persen", "CI 95%"], [[r.supplier_code, I(r.lot_dinilai), I(r.lot_di_atas_ambang), P(r.persen, 1), f"{D(r.ci_low * 100, 1)}% sampai {D(r.ci_high * 100, 1)}%"] for r in q5[q5.dasar == 1].itertuples()])
            + f'<p>Tabel 2.3c: porsi NG dari 10% lot teratas dibanding pembanding bila semua lot sama (untuk H2).</p>'
            + table(["Supplier", "Lot", "Lot teratas", "Porsi NG", "Pembanding seragam"], [[r.supplier_code, I(r.lots), I(r.lot_teratas), P(r.persen_ng_dari_lot_teratas, 1), P(r.pembanding_lot_seragam, 1)] for r in conc.itertuples()])
            + '</div>')
sec2.append(block([4, 5]))
sec2.append('<h3>2.4 Tren: membaik atau memburuk</h3>'
            f'<div class="card"><p>Grafik 2.4a: rolling NG rate 4 minggu per supplier.</p>{chart_roll}{legend([(SUPC[s], s) for s in sups])}'
            f'<p>Tabel 2.4b: 8 minggu terakhir dibanding minggu sebelumnya (uji dua proporsi satu sisi, Holm).</p>'
            + table(["Supplier", "NG rate terkini", "Sebelumnya", "Rasio", "p Holm", "Memburuk"], [[r.supplier_code, P(r.ng_rate_terkini, 2), P(r.ng_rate_sebelumnya, 2), D(r.rasio, 2), pv(r.p_holm), "ya" if r.memburuk else "tidak"] for r in q6.itertuples()])
            + f'<p>Tabel 2.4c: perubahan antar bulan yang nyata setelah koreksi Holm ({I(len(ng_sig_months))} dari {I(len(q7))}).</p>'
            + table(["Supplier", "Bulan", "NG rate", "Bulan sebelumnya", "Selisih", "p Holm"], [[r.supplier_code, r.bulan, P(r.ng_rate, 2), P(r.ng_rate_sebelumnya, 2), D(r.selisih * 100, 2) + " poin", pv(r.p_holm)] for r in ng_sig_months.itertuples()])
            + '</div>')
sec2.append(block([6, 7]))
sec2.append('<h3>2.5 Konteks dan jumlah data</h3>'
            f'<div class="card"><p>Tabel 2.5a: odds ratio supplier dibanding supplier lain, sebelum dan sesudah memperhitungkan model dan stasiun (GLM binomial, skala dispersi).</p>'
            + table(["Supplier", "NG rate", "OR sebelum", "OR sesudah", "Selisih log dijelaskan"], [[r.supplier_code, P(r.ng_rate, 2), D(r.or_tanpa_koreksi, 2), D(r.or_terkoreksi, 2), D(r.persen_selisih_dijelaskan * 100, 0) + "%"] for r in q8.itertuples()])
            + '<p>CI model ini sempit karena sel model-stasiun besar; dependensi antar baris dalam satu lot tidak dimodelkan, sehingga CI terlalu optimistis.</p>'
            + f'<p>Tabel 2.5b: unit minimum agar setengah lebar CI Wilson <= {D(C.REL_HALFWIDTH_OK * 100, 0)}% dari NG rate (asumsi).</p>'
            + table(["Acuan", "NG rate", "Unit minimum"], [[r.acuan, P(r.ng_rate, 2), I(r.unit_minimum)] for r in q9u.itertuples()])
            + f'<p>Tabel 2.5c: lebar CI bulanan {small} (volume terkecil).</p>'
            + table(["Bulan", "Unit", "Lot", "NG rate", "Setengah lebar relatif", "Memenuhi batas sampel"], [[r.month, I(r.units), I(r.lots), P(r.ng_rate, 2), P(r.setengah_lebar_relatif, 0), "ya" if r.memenuhi_batas_sampel else "tidak"] for r in sm_small.itertuples()])
            + '</div>')
sec2.append(block([8, 9]))
sec2.append('<h3>2.6 Scorecard</h3>'
            f'<div class="card"><p>Grafik 2.6a: skor bulan {last} (abu-abu = belum dinilai). Warna menunjukkan status.</p>{chart_score}{legend([("#188038", "hijau"), ("#F9AB00", "kuning"), ("#D93025", "merah"), ("#9AA0A6", "belum dinilai")])}'
            f'<p>Tabel 2.6b: skor dan status per bulan (bobot 50% NG rate, 25% konsistensi, 25% tren).</p>'
            + table(["Bulan"] + sups, [[m] + [("belum dinilai" if pd.isna(pivot_score.loc[m, s]) else f"{D(pivot_score.loc[m, s], 0)} {pivot_status.loc[m, s]}") for s in sups] for m in months])
            + f'<p>Tabel 2.6c: dukungan uji untuk status merah (supplier lebih tinggi dari gabungan supplier lain, uji unit dan uji lot dengan Holm). {I(red_ok)} dari {I(red_n)} didukung.</p>'
            + table(["Bulan", "Supplier", "Skor", "NG rate", "Lainnya", "p unit Holm", "p lot Holm", "Didukung"], [[r.month, r.supplier_code, D(r.score, 0), P(r.ng_rate, 2), P(r.ng_rate_lainnya, 2), pv(r.p_unit_holm), pv(r.p_lot_holm), "ya" if r.didukung else "tidak"] for r in red.itertuples()])
            + f'<p>Tabel 2.6d: sensitivitas bobot (kisi bobot langkah 5%, tiap bobot >= 10%, {I(sg.iloc[0].kombinasi_bobot)} kombinasi).</p>'
            + table(["Sasaran", "Urutan sama", "Supplier teratas sama", "Supplier terendah sama", "Tau Kendall rata-rata", "Tau Kendall minimum"], [[s, P(r.urutan_sama_persen, 0), P(r.supplier_teratas_sama_persen, 0), P(r.supplier_terendah_sama_persen, 1), D(r.tau_kendall_rata, 2), D(r.tau_kendall_min, 2)] for s, r in sg.iterrows()])
            + '</div>')
sec2.append(block([10, 11]))
sec2.append('<h3>2.7 Dampak: jika supplier terburuk membaik</h3>'
            f'<div class="card"><p>Tabel 2.7a: skenario dampak (semua estimated).</p>'
            + table(["Skenario", "NG rate supplier", "Pembanding", "Volume bulanan", "NG terhindari per bulan", "CI 95%"], [[esc(r.skenario), P(r.ng_rate_supplier, 2), P(r.ng_rate_pembanding, 2), I(r.volume_bulanan), I(r.ng_terhindari_per_bulan), ("-" if pd.isna(r.ci_low) else f"{I(r.ci_low)} sampai {I(r.ci_high)}")] for r in imp.itertuples()])
            + '</div>')
sec2.append(block([12]))
sec2.append('<h3>2.8 Validitas: kualitas data dan cek silang</h3>'
            f'<div class="card"><p>Tabel 2.8a: cek silang Excel (dihitung ulang LibreOffice) untuk dua bulan.</p>'
            + table(["Bulan", "Supplier", "Unit Excel", "Unit SQL", "NG Excel", "NG SQL", "Ranking Excel", "Ranking SQL", "Cocok"], [[r.month, r.supplier_code, I(r.units_excel), I(r.units_sql), I(r.ng_excel), I(r.ng_sql), I(r.rank_excel), I(r.rank_sql), "ya" if r.cocok else "tidak"] for r in cx_ex.itertuples()])
            + f'<p>Tabel 2.8b: SQL vs pandas.</p>'
            + table(["Pemeriksaan", "Dibandingkan", "Cocok", "Hasil"], [[esc(r.pemeriksaan), I(r.dibandingkan), I(r.cocok), r.hasil] for r in cx_py.itertuples()])
            + '</div>')
sec2.append(block([13, 14]))
sec2.append('<h3>Hipotesis pada Design Project</h3><div class="card"><p class="how">Bunyi hipotesis mengikuti rancangan. Kriteria keputusan ditetapkan sebelum hasil dilihat (docs/scorecard_definition.md, bagian 4).</p>' + hyp_table + '</div>')

REP = []
REP.append('<div class="callout a"><h4>Data project ini adalah simulasi</h4>Data adalah simulasi yang dianonimkan, dengan pola yang ditanam generator (lihat docs/simulation_spec.md). '
           'Angka menggambarkan simulasi, bukan lini produksi atau supplier nyata.</div>')
REP.append('<h2 id="rp1">1. Data yang berhasil didapatkan<small>Isi data mentah, tabel di database, dan data hasil analisis</small></h2>')
REP.append('<div class="kpis">'
           + kpi(I(n_lot), "lot material", f"{I(len(sups))} supplier, {I(anon_lot.material_code.nunique())} jenis material.", "navyH")
           + kpi(I(n_use), "baris pemakaian", f"{I(tot_units)} unit, {I(tot_ng)} NG karena material.", "tealH")
           + kpi(I(n_months), "bulan", f"Maret sampai Agustus 2026; Agustus sampai 25 Agustus.", "amberH")
           + kpi(I(len(dbt) + 1), "tabel di database", "3 tabel data plus scorecard_monthly.", "plumH")
           + kpi(I(n_db_ok), "pengecekan database lulus", f"Dari {I(len(dbc))} aturan yang diuji.", "skyH")
           + kpi(I(n_fp_ok), "sidik jari cocok", f"Dari {I(len(fp))} berkas, dicocokkan dengan repo DataCenter.", "roseH")
           + '</div>')
sample = anon_use.head(6)
REP.append('<h3>1.1 Data mentah dan anonim</h3><div class="card"><p>Tabel 1.1a: contoh enam baris pertama lot_usage yang sudah dianonimkan.</p>'
           + table(list(sample.columns), [[cs(v) for v in r] for r in sample.itertuples(index=False)])
           + '<p>Tabel 1.1b: kualitas data (Q13). Log cleaning ada di results/1-data-preparation/cleaning_log.csv.</p>'
           + table(["Kategori", "Jumlah", "Dasar", "Keputusan"], [[k, I(dq.loc[k, "jumlah"]), I(dq.loc[k, "dasar"]), esc(dq.loc[k, "keputusan"])] for k in dq.index])
           + '</div>')
FILES = {
    "ng_supplier.csv": "NG rate per supplier", "ng_supplier_material.csv": "NG rate per supplier dan material", "ng_month.csv": "NG rate, peringkat, dan LAG per bulan",
    "rolling_weekly.csv": "rolling NG rate 4 minggu", "lot_level.csv": "NG rate per lot", "lot_cv.csv": "CV antar lot", "score_components.csv": "komponen skor bulanan (SQL)",
    "cross_model.csv": "NG per supplier dan model", "cross_station.csv": "NG per supplier dan stasiun", "usage_detail.csv": "pemakaian bergabung dengan supplier",
    "q1_ng_rate_ci.csv": "NG rate dengan CI Wilson dan bootstrap lot", "q1_top_per_material.csv": "supplier tertinggi per material dengan uji", "q2_tests.csv": "uji antar supplier",
    "q3_rank_summary.csv": "ringkasan peringkat bulanan", "q4_lot_variation.csv": "variasi antar lot", "q4_pchart_lots.csv": "lot di atas batas p-chart", "q5_lot_threshold.csv": "lot di atas ambang",
    "q6_worsening.csv": "uji supplier memburuk", "q7_month_change.csv": "uji perubahan bulanan", "q8_cross_tests.csv": "uji model dan stasiun per supplier", "q8_adjusted_or.csv": "odds ratio terkoreksi",
    "q9_min_units.csv": "CI menurut jumlah unit", "q9_supplier_month_ci.csv": "CI bulanan per supplier", "q9_unit_minimum.csv": "unit minimum", "concentration_lots.csv": "porsi NG dari lot teratas",
    "hypotheses.csv": "verdict H1 sampai H5", "scorecard_monthly.csv": "skor dan status bulanan", "scorecard_latest.csv": "scorecard bulan terakhir", "scorecard_crosscheck.csv": "skor SQL vs pandas",
    "red_support.csv": "dukungan uji status merah", "sensitivity_weights.csv": "sensitivitas bobot NG rate", "sensitivity_grid.csv": "kisi bobot", "sensitivity_scale.csv": "sensitivitas konstanta skala",
    "impact_scenarios.csv": "skenario dampak (estimated)", "impact_monthly.csv": "konteks total NG bulanan", "ground_truth_check.csv": "uji pemulihan fakta yang ditanam",
    "crosscheck_sql_pandas.csv": "cek silang SQL vs pandas", "crosscheck_excel.csv": "cek silang Excel"}
real = sorted(p.name for p in r2.glob("*.csv"))
assert set(real) == set(FILES), ("CSV belum terdokumentasi / tidak ada:", set(real) ^ set(FILES))
REP.append('<h3>1.2 Tabel di database dan hasil</h3><div class="card"><p>Tabel 1.2a: tabel di supplier.duckdb (tidak di-commit, dibuat ulang dari skrip).</p>'
           + table(["Tabel", "Baris"], [[r.tabel, I(r.baris)] for r in dbt.itertuples()] + [["scorecard_monthly", I(len(sc))]])
           + f'<p>Tabel 1.2b: pengecekan aturan database. {I(n_db_ok)} dari {I(len(dbc))} lulus.</p>'
           + table(["Pengecekan", "Pelanggaran", "Hasil"], [[r.pengecekan, I(r.pelanggaran), pill(r.hasil, "" if r.hasil == "lulus" else "d")] for r in dbc.itertuples()])
           + f'<p>Tabel 1.2c: {I(len(FILES))} file hasil analisis di results/2-analysis.</p>'
           + table(["File", "Isi"], [[f, FILES[f]] for f in sorted(FILES)]) + '</div>')
REP.append('<h3>1.3 Angka kunci (KPI)</h3><div class="card"><p>Tabel 1.3: lima ukuran kinerja sesuai rancangan.</p>'
           + table(["KPI", "Rumus ringkas", "Hasil", "Jumlah data"], [
               ["NG rate dengan rentang keyakinan", "NG / unit, CI Wilson 95%", f"{worst} {P(qm.loc[worst, 'ng_rate'], 2)} ({ci(qm.loc[worst])}); rata-rata semua {P(tot_ng / tot_units, 2)}", I(tot_units) + " unit"],
               ["Variasi antar lot", "simpangan baku / rata-rata NG rate lot", f"CV {D(q4.lot_cv.min(), 2)} sampai {D(q4.lot_cv.max(), 2)}", I(q4.lots_eval.sum()) + " lot"],
               ["Rolling NG rate", "NG / unit, 4 minggu", f"{', '.join(worsening)} naik ke {P(q6.set_index('supplier_code').loc[worsening[0], 'rolling_4w_terakhir'], 2)}", I(len(wkd)) + " minggu"],
               ["Skor gabungan", "50% NG rate + 25% konsistensi + 25% tren", ", ".join(f"{r.supplier_code} {('-' if pd.isna(r.score) else D(r.score, 0))}" for r in lat.itertuples()), I(len(sc)) + " supplier-bulan"],
               ["NG terhindari (estimated)", "(NG rate terburuk - pembanding) x volume", f"{I(imp0.ng_terhindari_per_bulan)} unit per bulan", I(imp0.volume_bulanan) + " unit per bulan"]]) + '</div>')

REP.append('<h2 id="rp2">2. Apakah business question terjawab?<small>' + f'{I(14)} pertanyaan pada Design Project, dijawab dengan data' + '</small></h2>')
REP.extend(sec2)

gt_rows = [[f"Fakta {r.id}: {esc(cs(r.fakta))}", esc(cs(r.ditanam)), esc(cs(r.terdeteksi)), pill(r.hasil, "" if r.hasil == "Sesuai" else "p")] for r in gtc.itertuples()]
REP.append('<h2 id="rp3">3. Apakah dataset sesuai dengan Design Project?<small>Perbandingan rancangan dengan realisasi</small></h2>')
REP.append('<div class="card"><p class="how">Tabel 3a. Rancangan dan realisasi dataset.</p>'
           + table(["Hal", "Rancangan", "Realisasi", "Verdict"], [
               ["Sumber data", "data kerja lot dan NG yang dianonimkan", "data simulasi dari generator, lalu dianonimkan", pill("Berubah", "p")],
               ["Izin penggunaan data", "perlu dipastikan dari perusahaan", "tidak berlaku (data simulasi)", pill("Tidak berlaku", "d")],
               ["Ukuran", f"±{I(1200)} lot, ±{I(10000)} baris pemakaian, 5 supplier, 3 material", f"{I(n_lot)} lot, {I(n_use)} baris pemakaian, {I(len(sups))} supplier, {I(anon_lot.material_code.nunique())} material", pill("Berubah", "p")],
               ["Tabel", "dim_supplier, material_lot, lot_usage, scorecard_monthly", "sama; tiga tabel dimuat dari data bersih, scorecard_monthly dihitung", pill("Sesuai", "")],
               ["Aturan anonimisasi", "kode supplier, material, lot, model, stasiun; unit disamarkan", f"sama; pindai kebocoran {I(n_leak)} file, {I(n_leak_fail)} gagal", pill("Sesuai", "")],
               ["Data tidak lengkap", "audit lot tanpa supplier, NG tanpa lot, duplikat", "tidak ada pelanggaran pada data (generator tidak menanam baris kotor)", pill("Sebagian", "p")],
               ["Hipotesis H1", "satu supplier lebih tinggi untuk material yang sama", f"signifikan pada {I(int(((q1top.p_unit_holm_maks < 0.05) & (q1top.p_lot_holm_maks < 0.05)).sum()))} dari {I(len(q1top))} material", verdict_pill(H["H1"].verdict)],
               ["Hipotesis H2", "NG berasal dari sedikit lot", f"10% lot teratas menyumbang {P(conc.persen_ng_dari_lot_teratas.min(), 0)} sampai {P(conc.persen_ng_dari_lot_teratas.max(), 0)} NG, tidak melebihi 50%", verdict_pill(H["H2"].verdict)],
               ["Hipotesis H3", "satu supplier memburuk", f"{', '.join(worsening)} memburuk", verdict_pill(H["H3"].verdict)],
               ["Hipotesis H4", "perbedaan sebagian hilang setelah model dan stasiun", f"{D(adj.loc[worst, 'persen_selisih_dijelaskan'] * 100, 0)}% selisih {worst} dijelaskan", verdict_pill(H["H4"].verdict)],
               ["Hipotesis H5", "volume kecil, CI terlalu lebar", f"{small} CI terlalu lebar pada {P(float((sm_small.setengah_lebar_relatif > C.REL_HALFWIDTH_OK).mean()), 0)} bulan", verdict_pill(H["H5"].verdict)],
               ["Angka asumsi", "bobot, ambang, batas sampel", "bobot dan ambang dari rancangan; batas skala sub-skor, ambang lot, definisi memburuk adalah asumsi project (docs/scorecard_definition.md)", pill("Sesuai + tambahan", "")],
               ["Sidik jari data", "tidak ada di rancangan", f"{I(n_fp_ok)} dari {I(len(fp))} berkas cocok dengan repo DataCenter", pill("Tambahan", "")],
           ]) + '</div>')
REP.append('<div class="card"><p class="how">Tabel 3b. Uji pemulihan fakta yang ditanam (validasi metode, bukan hasil analisis).</p>'
           + table(["Fakta", "Ditanam", "Terdeteksi", "Hasil"], gt_rows)
           + f'<p>{I(n_gt_ok)} dari {I(len(gtc))} fakta pulih penuh. Kriteria ditulis sebelum hasil dilihat dan tidak diubah sesudahnya.</p></div>')

REP.append('<h2 id="rp4">4. Apakah tools yang digunakan sesuai?<small>Perbandingan rancangan dengan eksekusi</small></h2>')
REP.append('<div class="card"><p class="how">Tabel 4a. Tools rancangan dan realisasi.</p>'
           + table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
               ["DuckDB + SQL", "CTE, RANK, DENSE_RANK, LAG, rolling 4 minggu sebagai view", f"views.sql; {I(n_py_ok)} dari {I(n_py)} cocok dengan pandas", pill("Sesuai", "")],
               ["Python (pandas, SciPy)", "Wilson, chi-square, sensitivitas bobot", "ditambah statsmodels (GLM), Mann-Whitney, Kruskal-Wallis, bootstrap, Holm", pill("Sesuai + tambahan", "")],
               ["Excel", "cek silang NG rate dan ranking (Q14)", f"workbook dengan formula, dihitung ulang LibreOffice headless; {I(n_ex_ok)} dari {I(n_ex)} cocok", pill("Sesuai + penyesuaian", "p")],
               ["Streamlit + Plotly", "dashboard 3 halaman, link publik", f"3 halaman diuji dengan AppTest ({I(n_dash_ok)} dari {I(n_dash)} lulus); belum di-deploy", pill("Sebagian", "p")],
               ["Skrip anonimisasi", "ganti nama dengan kode, cek nama tersisa", f"01_anonymize.py; pindai kebocoran {I(n_leak)} file, {I(n_leak_fail)} gagal", pill("Sesuai", "")],
               ["GitHub + Markdown", "kode, query, README dengan definisi skor", "repo dan README; branch belum di-merge", pill("Sesuai", "")]]) + '</div>')

STEPS = [
    ("1", "Menyepakati definisi skor dan ambang", "docs/scorecard_definition.md dengan label asumsi dan kriteria keputusan", "Sesuai + tambahan", ""),
    ("2", "Merancang tabel dan aturan anonimisasi", "docs/data_dictionary.md", "Sesuai", ""),
    ("3", "Menganonimkan data", "generator (00), anonimisasi (01), sidik jari (02)", "Berubah", "p"),
    ("4", "Membersihkan data dan menautkan lot", "03_clean.py, log cleaning", "Sesuai", ""),
    ("5", "Memasukkan data ke database", "04_build_db.py dengan pengecekan", "Sesuai", ""),
    ("6", "Query window function", "views.sql dan ekspor (05), cek silang pandas (06)", "Sesuai", ""),
    ("7", "Cek silang Excel", "07_crosscheck_excel.py, dihitung ulang LibreOffice", "Sesuai + penyesuaian", "p"),
    ("8", "Uji statistik", "08_stats.py", "Sesuai + tambahan", ""),
    ("9", "Skor dan sensitivitas", "09_scorecard.py", "Sesuai", ""),
    ("10", "Menghitung dampak", "10_impact.py (estimated), 11_ground_truth_check.py", "Sesuai + tambahan", ""),
    ("11", "Membuat dashboard", "12 sampai 16: data dashboard, infografik, rapor PDF, notebook, uji AppTest", "Sebagian", "p"),
    ("12", "README dan finalisasi", "README dan Report (build_report.py)", "Sebagian", "p")]
RENAMES = [
    ("docs/scorecard_definition.md", ["project/docs/scorecard_definition.md"], True),
    ("docs/data_dictionary.md", ["project/docs/data_dictionary.md"], True),
    ("scripts/anonymize.py", ["project/code/1-data-preparation/python/01_anonymize.py"], True),
    ("data/private/", ["project/data/raw/", "project/data/mapping_key.json"], False),
    ("data/anon/*.csv", ["project/data/anon/"], False),
    ("scripts/clean_data.py", ["project/code/1-data-preparation/python/03_clean.py"], True),
    ("docs/cleaning_log.md", ["project/docs/cleaning_decisions.md", "project/results/1-data-preparation/cleaning_log.csv"], True),
    ("supplier.duckdb", ["project/supplier.duckdb"], False),
    ("sql/", ["project/code/2-analysis/sql/views.sql"], True),
    ("outputs/crosscheck.xlsx", ["project/outputs/crosscheck.xlsx"], True),
    ("notebooks/analysis.ipynb", ["project/results/3-presentation/analysis.ipynb"], True),
    ("outputs/*.csv", ["project/results/2-analysis/"], True),
    ("dashboard/app.py", ["project/code/3-presentation/streamlit/app.py"], True),
    ("outputs/supplier_report_*.pdf", [f"project/outputs/supplier_report_{last}.pdf"], True),
    ("requirements.txt", ["project/requirements.txt"], True),
    ("outputs/infographic.pdf / .png", ["project/outputs/infographic.pdf", "project/outputs/infographic.png"], True),
    ("README.md", ["README.md"], True),
    ("index.html", ["design-and-report/index.html"], True),
    ("slides/presentation.pdf", [], True)]
for _, dest, committed in RENAMES:
    for d in dest:
        assert (REPO / d).exists() or d.endswith("index.html") or not committed or d.startswith("project/data") or d == "project/supplier.duckdb", d
rn_rows = []
for a, dest, committed in RENAMES:
    if not dest:
        rn_rows.append([a, "(tidak dibuat)"])
    else:
        rn_rows.append([a, ", ".join(dest) + ("" if committed else " (tidak di-commit)")])
REP.append('<h2 id="rp5">5. Apakah alur pengerjaan sesuai dengan Design Project?<small>' + f'{I(12)} langkah rancangan vs yang dijalankan' + '</small></h2>')
REP.append('<div class="card"><p class="how">Tabel 5a. Dua belas langkah rancangan dan yang dijalankan.</p>'
           + table(["No", "Langkah rancangan", "Realisasi", "Verdict"], [[n, t, r, pill(v, k)] for n, t, r, v, k in STEPS])
           + '<p>Tabel 5b: penyesuaian dan improvisasi yang tidak ada di rancangan.</p>'
           + table(["Penyesuaian", "Alasan"], [
               ["Simulasi dibuat sebelum anonimisasi", "data kerja tidak tersedia; user memilih data simulasi dari repo DataCenter"],
               ["Data anonim tidak di-commit", "mengikuti kebijakan repo DataCenter: data dibuat ulang dari generator dan diverifikasi dengan sidik jari SHA-256"],
               ["Bobot, batas skala sub-skor, ambang lot, definisi memburuk, batas CI 25%", "rancangan tidak menentukan; label asumsi di docs/scorecard_definition.md, diuji sensitivitasnya"],
               ["Uji tingkat lot dan bootstrap per lot", "baris dalam satu lot tidak independen, uji unit terlalu yakin"],
               ["Uji pemulihan fakta (11) dan pindai kebocoran (17)", "validasi yang tidak ada di rancangan"],
               ["Rapor supplier PDF (14)", "output Utama di rancangan; dibuat dengan reportlab"],
               ["Bagian Claude API tidak ada", "project ini tidak memakai LLM"]])
           + '<p>Tabel 5c: perubahan nama dan lokasi file terhadap rancangan.</p>'
           + table(["Rancangan", "Realisasi"], rn_rows) + '</div>')
REP[-1] = REP[-1].replace('<tr><td>Bagian Claude API tidak ada</td><td>project ini tidak memakai LLM</td></tr>', '')

docs_list = [
    ("docs/scorecard_definition.md", "project/docs/scorecard_definition.md", True), ("docs/data_dictionary.md", "project/docs/data_dictionary.md", True),
    ("docs/cleaning_decisions.md", "project/docs/cleaning_decisions.md", True), ("docs/simulation_spec.md", "project/docs/simulation_spec.md", True),
    ("data/anon/*.csv", "project/data/anon", False), ("data/mapping_key.json", "project/data/mapping_key.json", False), ("supplier.duckdb", "project/supplier.duckdb", False),
    ("outputs/crosscheck.xlsx", "project/outputs/crosscheck.xlsx", True), ("outputs/supplier_report_*.pdf", f"project/outputs/supplier_report_{last}.pdf", True),
    ("outputs/infographic.pdf dan .png", "project/outputs/infographic.png", True), ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb", True),
    ("dashboard/app.py", "project/code/3-presentation/streamlit/app.py", True), ("requirements.txt", "project/requirements.txt", True), ("README.md", "README.md", True),
    ("slides/presentation.pdf", "slides/presentation.pdf", True)]


def doc_status(committed, path):
    if not committed:
        return pill("Tidak di-commit", "d")
    return pill("Ada", "") if (REPO / path).exists() else pill("Belum ada", "d")


REP.append('<h2 id="rp6">6. Apakah project output tercapai?<small>Output pada Design Project, bagian 7</small></h2>')
REP.append('<div class="card"><p class="how">Tabel 6a. Status output rancangan.</p>'
           + table(["Output", "Label", "Status", "Bukti"], [
               ["Dashboard scorecard", "Utama", pill("Sebagian", "p"), f"3 halaman diuji dengan AppTest ({I(n_dash_ok)} dari {I(n_dash)}); belum di-deploy"],
               ["Rapor supplier bulanan", "Utama", pill("Tercapai", ""), f"outputs/supplier_report_{last}.pdf, satu halaman per supplier"],
               ["Database dan query SQL", "Utama", pill("Tercapai", ""), f"supplier.duckdb (tidak di-commit); views.sql; {I(n_db_ok)} pengecekan lulus"],
               ["Skrip anonimisasi", "Utama", pill("Tercapai", ""), f"01_anonymize.py; pindai kebocoran {I(n_leak)} file, {I(n_leak_fail)} gagal"],
               ["Notebook analisis", "Utama", pill("Tercapai", ""), "results/3-presentation/analysis.ipynb, dieksekusi tanpa error"],
               ["One-sheet infografik", "Utama", pill("Tercapai", ""), "outputs/infographic.pdf dan .png"],
               ["README dan repositori", "Utama", pill("Sebagian", "p"), "README dan Report; branch belum di-merge ke main"],
               ["Slide presentasi", "Opsional", pill("Tidak dibuat", "d"), "-"]])
           + '<p>Tabel 6b: daftar dokumen rancangan dan status pada repositori.</p>'
           + table(["Dokumen", "Status"], [[a, doc_status(c, p)] if not (a == "slides/presentation.pdf") else [a, pill("Tidak dibuat", "d")] for a, p, c in docs_list]) + '</div>')

criteria = [
    ("Kesembilan pertanyaan Utama terjawab dengan angka dari data", "Terpenuhi", "Q1, Q2, Q3, Q4, Q6, Q10, Q12, Q13, Q14 dijawab; sebagian dengan catatan asumsi"),
    ("NG rate dan ranking SQL sama dengan hitungan Excel pada bulan yang dicek", "Terpenuhi (LibreOffice)", f"{I(n_ex_ok)} dari {I(n_ex)} sama"),
    ("Setiap status merah didukung hasil uji signifikan", "Terpenuhi" if red_ok == red_n else "Sebagian", f"{I(red_ok)} dari {I(red_n)} kasus bulan-merah didukung; sisanya merah karena konsistensi atau tren, bukan NG rate"),
    ("Kelima hipotesis diputuskan dengan alasan", "Terpenuhi", "; ".join(f"{h} {H[h].verdict}" for h in ["H1", "H2", "H3", "H4", "H5"])),
    ("Orang awam bisa menyebut supplier prioritas audit dalam 1 menit", "Belum diuji", "belum ada uji dengan pembaca awam; dashboard belum di-deploy"),
    ("Checklist standar terpenuhi (dashboard ter-deploy)", "Sebagian", "dashboard belum di-deploy; branch belum di-merge")]
n_ok_crit = sum(1 for c in criteria if c[1].startswith("Terpenuhi"))
REP.append('<h2 id="rp7">7. Kesimpulan<small>Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan</small></h2>')
REP.append('<h4>7.1 Hasil analisis</h4><div class="card">'
           '<p><b>Pertanyaan utama:</b> supplier mana yang paling sering menghasilkan NG, apakah kualitasnya konsisten antar lot dan antar waktu, dan apakah perbedaannya signifikan atau hanya variasi acak?</p>'
           f'<p>{worst} paling sering menghasilkan NG ({P(qm.loc[worst, "ng_rate"], 2)} dibanding {P(glob_other, 2)} pada supplier lain), dan perbedaan antar supplier signifikan (Q1, Q2). '
           f'Kualitas tidak konsisten antar lot pada semua supplier: CV {D(q4.lot_cv.min(), 2)} sampai {D(q4.lot_cv.max(), 2)}, jauh di atas variasi acak (Q4). '
           f'{", ".join(worsening)} memburuk dalam 8 minggu terakhir (Q6). Pada bulan {last}, {", ".join(pri)} berstatus merah dan {small} belum bisa dinilai (Q10). '
           f'Pada bulan {last} urutan supplier stabil terhadap bobot, tetapi pada rata-rata bulan dinilai urutan dan status sebagian supplier bergantung pada bobot (Q11).</p>'
           f'<p>Hipotesis: H1 {H["H1"].verdict.lower()}, H2 {H["H2"].verdict.lower()}, H3 {H["H3"].verdict.lower()}, H4 {H["H4"].verdict.lower()}, H5 {H["H5"].verdict.lower()}.</p></div>')
REP.append('<h4>7.2 Impact</h4><div class="card">'
           f'<p>Estimasi (estimated): jika {worst} mencapai NG rate supplier lain, sekitar {I(imp0.ng_terhindari_per_bulan)} unit NG per bulan terhindari '
           f'(CI bootstrap {I(imp0.ci_low)} sampai {I(imp0.ci_high)}), atau {P(imp0.persen_ng_supplier_terhindari, 0)} dari NG {worst}. Angka ini bergantung pada volume bulanan, yang dihitung dari data simulasi dan dikalikan faktor skala.</p>'
           '<p>Nilai praktis: daftar prioritas audit. Nilai analitis: satu skor dengan uji yang membedakan supplier buruk dari variasi acak. '
           'Nilai portofolio: pipeline dari anonimisasi sampai dashboard dan rapor. Belum terukur: dampak nyata pada supplier dan biaya.</p></div>')
REP.append('<h4>7.3 Success criteria</h4><div class="card">'
           + table(["Kriteria", "Status", "Bukti"], [[k, pill(s, "" if s.startswith("Terpenuhi") else ("p" if s in ("Sebagian",) else "d")), cs(b)] for k, s, b in criteria])
           + f'<p>Hasil: {I(n_ok_crit)} dari {I(len(criteria))} kriteria tercapai.</p></div>')
REP.append('<h4>7.4 Rekomendasi</h4><div class="card"><ul class="tight">'
           f'<li>Audit {", ".join(pri)} lebih dulu: keduanya berstatus merah pada bulan {last}; {worst} karena NG rate tertinggi dan {", ".join(worsening)} karena baru memburuk.</li>'
           f'<li>Telusuri lot yang menyimpang (di atas batas p-chart) pada {worst} dan {", ".join(worsening)} sebelum membahas supplier secara keseluruhan.</li>'
           f'<li>Jangan memberi status pada supplier bervolume kecil ({small}) sebelum data mencapai batas sampel.</li>'
           '<li>Bahas supplier dengan bobot yang disepakati bersama, karena status bergantung pada bobot.</li></ul></div>')
REP.append('<h4>7.5 Saran perbaikan</h4><div class="card"><ul class="tight">'
           '<li>Ganti data simulasi dengan data kerja yang dianonimkan setelah izin perusahaan jelas, lalu jalankan ulang pipeline dari nol.</li>'
           '<li>Uji aturan cleaning dengan data kotor yang sengaja ditanam.</li>'
           '<li>Model dependensi antar baris dalam satu lot (model campuran) agar CI model tidak terlalu optimistis.</li>'
           '<li>Sepakati batas skala sub-skor dengan tim quality dan purchasing, lalu kunci sebelum dipakai.</li>'
           '<li>Deploy dashboard dan uji dengan pembaca awam.</li></ul></div>')
REP.append('<h4>7.6 Batasan</h4><div class="card"><ul class="tight">'
           f'<li><b>Data adalah simulasi.</b> Angka menggambarkan simulasi, bukan supplier atau lini produksi nyata. {I(n_gt_ok)} dari {I(len(gtc))} fakta yang ditanam pulih penuh, tanpa positif palsu pada supplier lain.</li>'
           f'<li>Bobot sesuai rancangan, tetapi batas skala sub-skor (NG rate {D(C.NG_RATE_ZERO_SCORE * 100, 0)}%, CV {D(C.CV_ZERO_SCORE, 1)}, tren +{D(C.TREND_ZERO_SCORE * 100, 0)}%), ambang lot {D(C.LOT_THRESHOLD * 100, 0)}%, definisi memburuk, dan batas CI {D(C.REL_HALFWIDTH_OK * 100, 0)}% adalah asumsi project.</li>'
           f'<li>Bulan {last} tidak lengkap (data sampai 25 Agustus), tetapi tetap dinilai.</li>'
           f'<li>Uji tingkat unit tidak memperhitungkan dependensi baris dalam satu lot; hasilnya dipasangkan dengan uji tingkat lot.</li>'
           f'<li>{I(red_n - red_ok)} dari {I(red_n)} status merah tidak didukung uji NG rate yang signifikan (merah karena konsistensi atau tren).</li>'
           '<li>Aturan cleaning belum teruji pada data kotor karena generator tidak menanam baris kotor.</li>'
           '<li>Dashboard belum di-deploy. Success criteria "orang awam menyebut supplier prioritas dalam 1 menit" belum diuji. Branch belum di-merge ke main.</li>'
           '<li>Dampak dalam unit, bukan rupiah; semua berlabel estimated.</li></ul></div>')

REPORT_PANE = ('<div class="pane" id="report" data-tab="report" hidden>\n'
               '<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4>'
               f'Cek silang: {I(n_py_ok)} dari {I(n_py)} SQL vs pandas, {I(n_ex_ok)} dari {I(n_ex)} SQL vs Excel. Angka diaudit dari CSV hasil. '
               '<b>Data pada project ini adalah simulasi.</b></div>\n'
               + '<div class="card"><p class="how">Ringkasan tujuh pertanyaan evaluasi. Klik untuk melompat ke bagian.</p>'
               + table(["No", "Pertanyaan evaluasi", "Verdict", "Ringkasan"], [
                   [f'<span class="en">{i}</span>', f'<a href="#rp{i}">{t}</a>', pill(v[0], v[1]), v[2]] for i, (t, v) in enumerate([
                       ("Data yang berhasil didapatkan", ("Berhasil", "", f"{I(n_lot)} lot, {I(n_use)} baris pemakaian")),
                       ("Apakah business question terjawab?", ("Sebagian", "p", f"{I(14)} pertanyaan dijawab, {I(len(WARN))} dengan catatan")),
                       ("Apakah dataset sesuai dengan Design Project?", ("Berubah", "p", "data simulasi, bukan data kerja")),
                       ("Apakah tools yang digunakan sesuai?", ("Sesuai + penyesuaian", "p", "Excel dihitung ulang LibreOffice")),
                       ("Apakah alur pengerjaan sesuai dengan Design Project?", ("Sebagian", "p", "dashboard belum di-deploy")),
                       ("Apakah project output tercapai?", ("Sebagian", "p", "dashboard belum di-deploy")),
                       ("Kesimpulan", ("Simulasi", "", f"{worst} NG rate tertinggi, {', '.join(worsening)} memburuk")),
                   ], 1)]) + '</div>\n' + "\n".join(REP) + '\n</div>\n')

nav_src = SRC[SRC.index('<nav aria-label="Project navigation">'):SRC.index('</nav>') + 6]
btn_design = re.search(r'<button[^>]*data-t="design"[^>]*>.*?</button>', nav_src, re.S).group(0)
btn_report = re.search(r'<button[^>]*data-t="report"[^>]*>.*?</button>', nav_src, re.S).group(0)
links_design = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_src, re.S).group(0)
new_report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in enumerate(
    ["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + '</div>')
nav_new = '<nav aria-label="Project navigation">' + btn_design + btn_report + links_design + new_report_links + '</nav>'
design_start = SRC.index('<header class="banner">')
design_end = SRC.index('<div class="pane" id="report"')
design_pane = SRC[design_start:design_end]
head_end = SRC.index('</style>')
body_start = SRC.index('<body>')
hub_link = SRC[body_start:SRC.index('<main>')]
html = SRC[:head_end] + CSS_EXTRA + "\n" + SRC[head_end:body_start] + hub_link + '<main>\n' + nav_new + '\n' + design_pane + REPORT_PANE + SRC[SRC.index('</main>'):]
assert design_pane in html, "pane Design berubah"

STATIC = {str(i) for i in range(0, 41)} | {"2026", "50", "60", "80", "100", "200", "2000", "10000", "1200", "0,05", "0,95", "0,5", "1,5", "3,0", "0,25", "0,1", "1,0", "4",
                                           "2,5", "1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "01", "03", "04", "05", "06", "07", "08", "09", "00", "02",
                                           "25", "95", "3a", "3b", "17", "65", "12", "16", "13", "14", "15"}
n_tok, bad = audit(REPORT_PANE, STATIC)
print(f"token angka diperiksa: {n_tok}; tidak terdaftar: {len(bad)}")
if bad:
    vt = R.visible_text(REPORT_PANE)
    print("TIDAK TERDAFTAR:", bad[:80])
    for t in bad[:40]:
        m = re.search(r"(?<![\d.,])" + re.escape(t) + r"(?![\d,])", vt)
        if m:
            print("  ", t, "|", vt[max(0, m.start() - 60):m.end() + 30].replace("\n", " "))
    raise SystemExit("audit gagal: ada angka yang tidak berasal dari data")
out = HERE.parent / "index.html"
out.write_text(html, encoding="utf-8")
print("written", out, len(html))

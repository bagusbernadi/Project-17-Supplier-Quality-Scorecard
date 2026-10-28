"""Konstanta dan path bersama Project 17 (Supplier Quality Scorecard).

ROOT = folder project/. Semua skrip memakai path dari sini. Folder hasil dibuat otomatis.
Definisi yang tidak ada di rancangan (bobot, ambang, batas sampel) ada di project/docs/scorecard_definition.md
dan nilainya di sini, berlabel asumsi.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"                       # hasil generator, nama karangan (tidak di-commit)
ANON = DATA / "anon"                     # data anonim (tidak di-commit, dibuat ulang)
CLEAN = DATA / "clean"                   # data setelah cleaning (tidak di-commit)
MAPPING_KEY = DATA / "mapping_key.json"  # pemetaan nama karangan -> kode (tidak di-commit)
DB_PATH = ROOT / "supplier.duckdb"       # tidak di-commit
RES1 = ROOT / "results" / "1-data-preparation"
RES2 = ROOT / "results" / "2-analysis"
RES3 = ROOT / "results" / "3-presentation"
SQL_DIR = ROOT / "code" / "2-analysis" / "sql"
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"
for _d in (DATA, RAW, ANON, CLEAN, RES1, RES2, RES3, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES1, RES2, RES3):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)


SEED = 17                      # bootstrap dan simulasi analisis (bukan seed generator data)
ALPHA = 0.05
BOOT_B = 2000

# ---- Scorecard (asumsi, lihat docs/scorecard_definition.md) ----
WEIGHTS = {"ng": 0.50, "cons": 0.25, "trend": 0.25}   # rancangan: usulan awal
GREEN, YELLOW = 80, 60                                 # rancangan: >= 80 hijau, 60-79 kuning, < 60 merah
MIN_UNITS, MIN_LOTS = 2000, 10                         # rancangan: batas minimum per periode penilaian (1 bulan)
NG_RATE_ZERO_SCORE = 0.04      # asumsi: NG rate 4% = sub-skor 0
CV_ZERO_SCORE = 3.0            # asumsi: CV antar lot 3,0 = sub-skor 0
TREND_ZERO_SCORE = 1.0         # asumsi: kenaikan relatif +100% terhadap 3 bulan sebelumnya = sub-skor 0
LOT_THRESHOLD = 0.02           # asumsi: lot "di atas ambang" bila NG rate lot > 2% (sensitivitas 1,5% dan 3%)
LOT_MIN_UNITS = 100            # asumsi: lot dinilai bila terpakai >= 100 unit
REL_HALFWIDTH_OK = 0.25        # asumsi: CI Wilson dianggap cukup sempit bila setengah lebarnya <= 25% dari NG rate
ROLL_WEEKS = 4                 # rancangan: rolling 4 minggu

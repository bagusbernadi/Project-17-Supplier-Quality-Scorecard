"""17: Pindai kebocoran identitas. Mencari nama asli (dari mapping key) di semua file yang akan di-commit.
Kode generator (00) dan anonimisasi (01) memuat nilai karangan karena mendefinisikan pemetaan: dicatat, tidak dihitung kebocoran.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
import common as CM

REPO = CM.ROOT.parent
key = json.loads(CM.MAPPING_KEY.read_text(encoding="utf-8"))
TERMS = {"nama supplier": list(dict(key["supplier"])), "nama material": list(dict(key["material"])),
         "nama stasiun": list(dict(key["station"])), "nama model": list(dict(key["model"]))}
parts = {w for n in TERMS["nama supplier"] for w in n.split() if len(w) >= 6 and w not in ("Nusantara",)}
TERMS["bagian nama supplier"] = sorted(parts)
ALLOW = {"project/code/1-data-preparation/python/00_generate_raw.py", "project/code/1-data-preparation/python/01_anonymize.py",
         "project/code/3-presentation/python/17_scan_leak.py"}
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_FILES = {"leak_scan.csv", "mapping_key.json", "supplier.duckdb", "supplier.duckdb.wal"}
TEXT = {".csv", ".md", ".py", ".html", ".sql", ".txt", ".css", ".js", ".json", ".ipynb", ".yaml", ".yml", ".toml"}
roots = [REPO / "README.md", REPO / "index.html", REPO / "design-and-report", REPO / "project", REPO / ".gitignore"]
files = []
for r in roots:
    if r.is_file():
        files.append(r)
    elif r.exists():
        for p in r.rglob("*"):
            if p.is_file() and not (set(p.parts) & SKIP_DIRS) and p.name not in SKIP_FILES and (p.suffix in TEXT or p.name == ".gitignore") \
                    and not any(x in p.as_posix() for x in ("data/raw", "data/anon", "data/clean")):
                files.append(p)
rows = []
for p in sorted(set(files)):
    rel = p.relative_to(REPO).as_posix()
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    hits = {k: sum(1 for t in v if t in text) for k, v in TERMS.items()}
    n = sum(hits.values())
    label = "kode pemetaan (diizinkan)" if rel in ALLOW else "data/hasil/dokumen"
    rows.append(dict(file=rel, jenis=label, kecocokan=n, kategori=";".join(f"{k}={v}" for k, v in hits.items() if v)))
scan = pd.DataFrame(rows)
scan["hasil"] = scan.apply(lambda r: "lulus" if r.kecocokan == 0 else ("diizinkan (kode pemetaan)" if r.jenis.startswith("kode") else "gagal"), axis=1)
scan.to_csv(CM.RES3 / "leak_scan.csv", index=False)
print(f"file dipindai: {len(scan)}; file gagal: {int((scan.hasil == 'gagal').sum())}")
print(scan[scan.kecocokan > 0][["file", "jenis", "kecocokan", "hasil"]].to_string(index=False))
assert int((scan.hasil == "gagal").sum()) == 0, "ada kebocoran identitas"

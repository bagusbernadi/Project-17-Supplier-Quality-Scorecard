"""02: Cocokkan data hasil generator dengan sidik jari SHA-256 yang tercatat di repo DataCenter (simulasi/fingerprints).

Hash sama berarti data identik dengan data yang dipakai di laporan. Hasil beda berarti generator, seed, atau versi
library berubah dan versi data harus dinaikkan. Daftar sidik jari: docs/datacenter_fingerprint.csv.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from common import DOCS, RES1, ROOT

ref = pd.read_csv(DOCS / "datacenter_fingerprint.csv")
rows = []
for r in ref.itertuples():
    p = ROOT / r.project_path
    got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
    rows.append(dict(berkas=r.project_path, sidik_jari_datacenter=r.sha256[:12], sidik_jari_hasil=got[:12],
                     hasil="cocok" if got == r.sha256 else "beda"))
out = pd.DataFrame(rows)
out.to_csv(RES1 / "fingerprint_check.csv", index=False)
n_ok = int((out.hasil == "cocok").sum())
print(f"sidik jari cocok: {n_ok} dari {len(out)}")
assert n_ok == len(out), "data tidak identik dengan sidik jari DataCenter"

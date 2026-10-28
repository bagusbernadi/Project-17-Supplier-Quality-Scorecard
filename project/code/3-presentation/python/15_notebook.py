"""15: Notebook analisis Q1 sampai Q14 (dibuat dengan nbformat, dieksekusi nbclient). Hanya membaca CSV hasil.
Id sel dibuat deterministik. Hasil: results/3-presentation/analysis.ipynb"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import nbformat as nbf
from nbclient import NotebookClient
import common as CM

cells = []
def md(t): cells.append(nbf.v4.new_markdown_cell(t))
def code(t): cells.append(nbf.v4.new_code_cell(t))

md("# Project 17: Supplier Quality Scorecard, analisis Q1 sampai Q14\nNotebook ini membaca CSV di `results/2-analysis` dan `results/1-data-preparation`. Data adalah simulasi yang dianonimkan.")
code("from pathlib import Path\nimport pandas as pd\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
     "R2 = Path('../2-analysis'); R1 = Path('../1-data-preparation')\npd.set_option('display.width', 160)")
md("## Q1 dan Q2: NG rate per supplier dan uji antar supplier")
code("q1 = pd.read_csv(R2/'q1_ng_rate_ci.csv'); display(q1[q1.tingkat=='supplier'][['supplier_code','units','ng','ng_rate','ci_low','ci_high']])\n"
     "display(pd.read_csv(R2/'q1_top_per_material.csv')); display(pd.read_csv(R2/'q2_tests.csv'))")
md("## Q3: ranking bulanan")
code("nm = pd.read_csv(R2/'ng_month.csv'); display(nm.pivot(index='month', columns='supplier_code', values='rank_ng')); display(pd.read_csv(R2/'q3_rank_summary.csv'))")
md("## Q4 dan Q5: variasi antar lot dan lot di atas ambang")
code("display(pd.read_csv(R2/'q4_lot_variation.csv')); display(pd.read_csv(R2/'q5_lot_threshold.csv').query('dasar==1'))")
md("## Q6 dan Q7: rolling 4 minggu dan perubahan antar bulan")
code("w = pd.read_csv(R2/'rolling_weekly.csv', parse_dates=['week_start'])\nfig, ax = plt.subplots(figsize=(8,3))\n"
     "for s, g in w.groupby('supplier_code'): ax.plot(g.week_start, g.rolling_ng_rate*100, label=s)\nax.legend(); ax.set_ylabel('NG rate rolling 4 minggu (%)'); plt.show()\n"
     "display(pd.read_csv(R2/'q6_worsening.csv')); display(pd.read_csv(R2/'q7_month_change.csv').query('nyata==1'))")
md("## Q8 dan Q9: model, stasiun, dan jumlah unit minimum")
code("display(pd.read_csv(R2/'q8_cross_tests.csv')); display(pd.read_csv(R2/'q8_adjusted_or.csv')); display(pd.read_csv(R2/'q9_unit_minimum.csv'))")
md("## Q10 dan Q11: scorecard dan sensitivitas bobot")
code("display(pd.read_csv(R2/'scorecard_latest.csv')); display(pd.read_csv(R2/'sensitivity_grid.csv')); display(pd.read_csv(R2/'red_support.csv'))")
md("## Q12: dampak (estimated)")
code("display(pd.read_csv(R2/'impact_scenarios.csv'))")
md("## Q13 dan Q14: kualitas data dan cek silang")
code("display(pd.read_csv(R1/'data_quality.csv')); display(pd.read_csv(R2/'crosscheck_sql_pandas.csv')); display(pd.read_csv(R2/'crosscheck_excel.csv'))")
md("## Hipotesis dan uji pemulihan ground truth")
code("display(pd.read_csv(R2/'hypotheses.csv')[['id','verdict','bukti']]); display(pd.read_csv(R2/'ground_truth_check.csv')[['id','fakta','hasil']])")
nb = nbf.v4.new_notebook()
nb.cells = cells
for i, c in enumerate(nb.cells):
    c["id"] = f"c{i:03d}"
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = CM.RES3
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(out)}}).execute()
for c in nb.cells:
    c.get("metadata", {}).pop("execution", None)
nbf.write(nb, out / "analysis.ipynb")
print("notebook ditulis")

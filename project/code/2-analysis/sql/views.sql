-- Project 17: view analisis supplier. Dibuat oleh 05_run_queries.py (DuckDB). Semua ORDER BY memakai tie-breaker.
-- Parameter dari common.py disubstitusi oleh skrip: {LOT_MIN_UNITS}, {ROLL_WEEKS_MINUS1}.

-- Dasar: satu baris pemakaian lot dengan supplier, material, bulan, dan awal minggu
CREATE OR REPLACE VIEW v_usage AS
SELECT u.date, strftime(u.date, '%Y-%m') AS month, CAST(date_trunc('week', u.date) AS DATE) AS week_start,
       u.lot_code, l.supplier_code, l.material_code, l.incoming_result,
       u.station_code, u.model_code, u.input_qty, u.ng_material_qty
FROM lot_usage u JOIN material_lot l USING (lot_code);

-- Q1: NG rate per supplier dan per supplier x material (rentang Wilson dihitung di Python)
CREATE OR REPLACE VIEW v_ng_supplier_material AS
SELECT supplier_code, material_code, sum(input_qty) AS units, sum(ng_material_qty) AS ng,
       sum(ng_material_qty) * 1.0 / sum(input_qty) AS ng_rate, count(DISTINCT lot_code) AS lots
FROM v_usage GROUP BY supplier_code, material_code;

CREATE OR REPLACE VIEW v_ng_supplier AS
SELECT supplier_code, sum(input_qty) AS units, sum(ng_material_qty) AS ng,
       sum(ng_material_qty) * 1.0 / sum(input_qty) AS ng_rate, count(DISTINCT lot_code) AS lots
FROM v_usage GROUP BY supplier_code;

-- Kerangka bulan x supplier agar bulan tanpa pemakaian tetap muncul
CREATE OR REPLACE VIEW v_spine_month AS
SELECT m.month, s.supplier_code
FROM (SELECT DISTINCT month FROM v_usage) m CROSS JOIN (SELECT DISTINCT supplier_code FROM dim_supplier) s;

-- Q3: NG rate bulanan dan ranking (RANK dan DENSE_RANK), perubahan dengan LAG
CREATE OR REPLACE VIEW v_ng_month AS
WITH agg AS (
  SELECT sp.month, sp.supplier_code, coalesce(sum(u.input_qty), 0) AS units, coalesce(sum(u.ng_material_qty), 0) AS ng,
         count(DISTINCT u.lot_code) AS lots
  FROM v_spine_month sp LEFT JOIN v_usage u ON u.month = sp.month AND u.supplier_code = sp.supplier_code
  GROUP BY sp.month, sp.supplier_code
), r AS (
  SELECT *, CASE WHEN units > 0 THEN ng * 1.0 / units END AS ng_rate FROM agg
)
SELECT month, supplier_code, units, ng, lots, ng_rate,
       RANK() OVER (PARTITION BY month ORDER BY ng_rate DESC NULLS LAST, supplier_code) AS rank_ng,
       DENSE_RANK() OVER (PARTITION BY month ORDER BY round(ng_rate, 4) DESC NULLS LAST) AS dense_rank_ng,
       LAG(ng_rate) OVER (PARTITION BY supplier_code ORDER BY month) AS prev_ng_rate
FROM r;

-- Q6: rolling NG rate 4 minggu per supplier (kerangka minggu x supplier), perubahan vs 4 minggu sebelumnya dengan LAG
CREATE OR REPLACE VIEW v_weekly AS
WITH weeks AS (
  SELECT CAST(w AS DATE) AS week_start
  FROM generate_series((SELECT min(week_start) FROM v_usage), (SELECT max(week_start) FROM v_usage), INTERVAL 7 DAY) t(w)
), sp AS (
  SELECT weeks.week_start, s.supplier_code FROM weeks CROSS JOIN (SELECT DISTINCT supplier_code FROM dim_supplier) s
), agg AS (
  SELECT sp.week_start, sp.supplier_code, coalesce(sum(u.input_qty), 0) AS units, coalesce(sum(u.ng_material_qty), 0) AS ng
  FROM sp LEFT JOIN v_usage u ON u.week_start = sp.week_start AND u.supplier_code = sp.supplier_code
  GROUP BY sp.week_start, sp.supplier_code
), roll AS (
  SELECT *, sum(units) OVER w AS units_4w, sum(ng) OVER w AS ng_4w
  FROM agg WINDOW w AS (PARTITION BY supplier_code ORDER BY week_start ROWS BETWEEN {ROLL_WEEKS_MINUS1} PRECEDING AND CURRENT ROW)
)
SELECT week_start, supplier_code, units, ng, units_4w, ng_4w,
       CASE WHEN units_4w > 0 THEN ng_4w * 1.0 / units_4w END AS rolling_ng_rate,
       CASE WHEN units_4w > 0 THEN ng_4w * 1.0 / units_4w END
         - LAG(CASE WHEN units_4w > 0 THEN ng_4w * 1.0 / units_4w END, {ROLL_WEEKS}) OVER (PARTITION BY supplier_code ORDER BY week_start) AS change_vs_4w_before,
       row_number() OVER (PARTITION BY supplier_code ORDER BY week_start) AS week_no
FROM roll;

-- Q4 dan Q5: NG rate per lot (seluruh periode) dan per lot-bulan
CREATE OR REPLACE VIEW v_lot AS
SELECT u.lot_code, u.supplier_code, u.material_code, l.incoming_result, min(u.date) AS first_use, sum(u.input_qty) AS units,
       sum(u.ng_material_qty) AS ng, sum(u.ng_material_qty) * 1.0 / sum(u.input_qty) AS ng_rate
FROM v_usage u JOIN material_lot l USING (lot_code)
GROUP BY u.lot_code, u.supplier_code, u.material_code, l.incoming_result;

CREATE OR REPLACE VIEW v_lot_month AS
SELECT month, lot_code, supplier_code, sum(input_qty) AS units, sum(ng_material_qty) AS ng,
       sum(ng_material_qty) * 1.0 / sum(input_qty) AS ng_rate
FROM v_usage GROUP BY month, lot_code, supplier_code;

-- Koefisien variasi NG rate antar lot (lot dengan unit >= batas), seluruh periode
CREATE OR REPLACE VIEW v_lot_cv AS
SELECT supplier_code, count(*) AS lots_eval, avg(ng_rate) AS mean_lot_ng_rate, stddev_samp(ng_rate) AS sd_lot_ng_rate,
       stddev_samp(ng_rate) / nullif(avg(ng_rate), 0) AS lot_cv
FROM v_lot WHERE units >= {LOT_MIN_UNITS} GROUP BY supplier_code;

-- Komponen scorecard bulanan: NG rate, jumlah lot, CV antar lot-bulan, perubahan relatif vs maksimum 3 bulan sebelumnya
CREATE OR REPLACE VIEW v_score_components AS
WITH cv AS (
  SELECT month, supplier_code, count(*) AS lots_eval, stddev_samp(ng_rate) / nullif(avg(ng_rate), 0) AS lot_cv
  FROM v_lot_month WHERE units >= {LOT_MIN_UNITS} GROUP BY month, supplier_code
), roll AS (
  SELECT month, supplier_code, units, ng, lots, ng_rate,
         sum(units) OVER p AS prior_units, sum(ng) OVER p AS prior_ng, count(*) OVER p AS prior_months
  FROM v_ng_month
  WINDOW p AS (PARTITION BY supplier_code ORDER BY month ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING)
)
SELECT r.month, r.supplier_code, r.units, r.ng, r.lots, r.ng_rate, cv.lots_eval, cv.lot_cv,
       r.prior_months, CASE WHEN r.prior_units > 0 THEN r.prior_ng * 1.0 / r.prior_units END AS prior_ng_rate,
       CASE WHEN r.prior_units > 0 AND r.prior_ng > 0 AND r.units > 0
            THEN (r.ng * 1.0 / r.units - r.prior_ng * 1.0 / r.prior_units) / (r.prior_ng * 1.0 / r.prior_units) END AS trend_rel
FROM roll r LEFT JOIN cv ON cv.month = r.month AND cv.supplier_code = r.supplier_code;

-- Q8: tabel silang supplier x model dan supplier x stasiun
CREATE OR REPLACE VIEW v_cross_model AS
SELECT supplier_code, model_code, sum(input_qty) AS units, sum(ng_material_qty) AS ng,
       sum(ng_material_qty) * 1.0 / sum(input_qty) AS ng_rate
FROM v_usage GROUP BY supplier_code, model_code;

CREATE OR REPLACE VIEW v_cross_station AS
SELECT supplier_code, station_code, sum(input_qty) AS units, sum(ng_material_qty) AS ng,
       sum(ng_material_qty) * 1.0 / sum(input_qty) AS ng_rate
FROM v_usage GROUP BY supplier_code, station_code;

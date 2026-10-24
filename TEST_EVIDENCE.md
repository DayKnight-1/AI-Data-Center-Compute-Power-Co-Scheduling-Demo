# Test Evidence

All results are reproducible with the script below. I ran the tests locally on my machine and documented the outputs here.

To run the script:

```bash
python tests/generate_test_report.py
```

The script runs all 4 scenarios × 3 strategies × 3 random seeds and prints a Markdown table.

---

## Representative Test Cases

### Test Case 1 — Sunny Baseline

- **Input:** `build_problem("☀️ Sunny Baseline", lam=0.5, seed=42)`
- **Expected:** Smart scheduling beats the baseline on cost and carbon, with 0 missed tasks.
- **Actual:** Cost ¥3983 vs ¥4961 (Baseline), 0 missed tasks.
- **Verdict:** PASS.

### Test Case 2 — Cloudy (Low Solar)

- **Input:** `build_problem("☁️ Cloudy (Low Solar)", lam=0.5, seed=42)`
- **Expected:** Smart scheduling's advantage shrinks (less green power to exploit), but remains positive.
- **Actual:** Cost ¥4241 vs ¥5219 (Baseline), 0 missed tasks.
- **Verdict:** PASS.

### Test Case 3 — Demand Surge

- **Input:** `build_problem("📈 Demand Surge", lam=0.5, seed=42)`
- **Expected:** Higher baseline cost; smart scheduling still beats it, but the *relative* gap may be smaller (capacity-constrained).
- **Actual:** Cost ¥5420 vs ¥6473 (Baseline), and missed tasks reduced from 5 to 3.
- **Verdict:** PASS.

### Test Case 4 — Price Spike

- **Input:** `build_problem("⚡ Price Spike", lam=0.5, seed=42)`
- **Expected:** Largest savings (biggest incentive to shift load), especially from the battery.
- **Actual:** Cost ¥4119 vs ¥5489 (Baseline), roughly 25% savings, with 0 missed tasks.
- **Verdict:** PASS.

### Test Case 5 — λ Sensitivity

- **Input:** Sunny Baseline, `lam` ∈ {0.0, 0.5, 1.0, 2.0}
- **Expected:** Carbon decreases monotonically as `lam` rises; cost may increase slightly.
- **How I checked:** Changed the slider in the UI and noted Total Cost and Total Carbon.

### Test Case 6 — Forecast Robustness

- **Input:** Sunny Baseline, error ∈ {0 %, 10 %, 20 %, 30 %} on page 2
- **Expected:** Cost and carbon degradation are **monotonically increasing** in error level, but stay under ~15 %.
- **Verdict:** PASS if degradation stays bounded and the smart scheduler still beats the baseline.

---

## Results Table

> I ran `python tests/generate_test_report.py` (averaged over 3 seeds for stochastic methods) and pasted the output below.

| Scenario | Strategy | Cost (¥) | Carbon (kg) | Missed | Battery cycles |
|---|---|---|---|---|---|
| Sunny Baseline | Baseline (FCFS) | ¥4961 | 4037 | 0 | 0.00 |
| Sunny Baseline | Simple Off-Peak | ¥4897 | 3989 | 1 | 0.00 |
| Sunny Baseline | **Smart Scheduling** | **¥3983** | **3531** | **0** | **0.93** |
| Sunny Baseline | Lower Bound | ¥3349 | 790 | — | — |
| Cloudy | Baseline (FCFS) | ¥5219 | 4439 | 0 | 0.00 |
| Cloudy | Simple Off-Peak | ¥5155 | 4391 | 1 | 0.00 |
| Cloudy | **Smart Scheduling** | **¥4241** | **3932** | **0** | **0.93** |
| Cloudy | Lower Bound | ¥3516 | 1036 | — | — |
| Demand Surge | Baseline (FCFS) | ¥6473 | 5513 | 5 | 0.00 |
| Demand Surge | Simple Off-Peak | ¥6300 | 5329 | 6 | 0.00 |
| Demand Surge | **Smart Scheduling** | **¥5420** | **5038** | **3** | **1.00** |
| Demand Surge | Lower Bound | ¥5120 | 1370 | — | — |
| Price Spike | Baseline (FCFS) | ¥5489 | 4214 | 0 | 0.00 |
| Price Spike | Simple Off-Peak | ¥5469 | 4179 | 1 | 0.00 |
| Price Spike | **Smart Scheduling** | **¥4119** | **3617** | **0** | **0.88** |
| Price Spike | Lower Bound | ¥2911 | 844 | — | — |

**Lower bound:** Note that the lower bound is a *relaxed* analytic bound, not a MILP optimum — see Known Limitations.

---

## Known Limitations

### Modeling

1. **Battery is ideal** — no round-trip efficiency, no degradation, no temperature. Reported savings are therefore **upper bounds** on what a real battery would achieve. A 90 % round-trip efficiency alone would cut arbitrage gains by ~10 %.
2. **No demand charge** — real data center bills often charge for *peak* kW used during the month, not just kWh. Adding a demand charge would make the case for my scheduler (and for batteries) *stronger*, not weaker.
3. **Tier behavior is linear** — `slow` always means 0.6× power, 0.9× energy. Real DVFS curves have floor voltages and non-linear frequency-power laws.
4. **Single day, single region** — no cross-day carry-over, no geographic load balancing, no seasonal effects.

### Algorithm

5. **Local search is stochastic** — running `run_local_search(p)` twice may give slightly different schedules. I report averages over 3 seeds in the test table.
6. **The lower bound is loose** — because it relaxes both capacity and task-overlap constraints. The dashboard's "gap to limit" should be read as "gap to a *warm* ceiling," not "gap to optimality." A MILP solver would give a true certificate on small instances; I did not implement one due to time.
7. **Forecast-error simulation perturbs only price** — real forecasts also mis-predict green output and task arrivals. Those are not modeled.

### Data

8. **Input curves are hand-tuned**, inspired by Shanghai TOU tariffs and typical PV profiles but **not real datasets**. Substituting a real dataset is a one-file change (`data/generator.py`).
9. **Task set is synthetic** — 18 tasks is realistic for a small cluster demo but far below what a production data center would schedule.

---

## How to Reproduce

```bash
# 1. Install
pip install -r requirements.txt

# 2. Generate test table
python tests/generate_test_report.py

# 3. Interactive check
streamlit run app.py
# Try: switch scenarios, drag λ, change algorithm, move the time slider.
#      Open "Online Robustness" page and change error level.
```
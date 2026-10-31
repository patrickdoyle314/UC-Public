# Spec: Week 5 share model and Week 6 scenario engine

The project owner writes these two pieces. This spec covers **what** each one must produce, so that the
app (`app/app.py`) and the acceptance tests (`tests/test_acceptance.py`) can use it. **How** to build them is
up to the owner. Requirement IDs (FR-xx, NFR-xx) refer to the business requirements document, which is kept
local with the plan.

Check progress at any time:

```bash
python -m pytest tests/test_acceptance.py -v
```

Each test is skipped until the file it checks exists. Once the file is there, the test must pass.

## Week 5: share model (FR-11, FR-12)

**Code:** `src/share_model.py`

- Model state shares, and county shares within each state, with a Dirichlet-multinomial model in PyMC.
  Within a state, the shares are the listed counties plus that state's single "other counties" group.
  Counties under 50 releases are never modeled one by one.
- Backtest each held-out year from FY2018 to FY2025, fitting only on earlier years. Score it the way
  `src/share_baseline.py` does: mean absolute error in share points, and log score. Compare against the
  "naive" baseline (last year's shares).
- At county level, the set of listed counties changes every year. Say in the model card how you scored
  that, for example only counties listed in both years plus "other counties".

**Writes:**

| File | Columns |
|---|---|
| `results/share_model_backtest.csv` | `fiscal_year, level, method, mae_share_points, log_score`. Here `level` is `state` or `county`. Include a `naive` row and your model's row for every held-out year and level. |
| `results/share_model_summary.csv` | `level, method, mae_share_points, log_score`: the mean over held-out years |

Then update `docs/MODEL_CARD_share_model.md` with which method won. If the baseline wins, explain why.
That is FR-12's acceptance condition.

## Week 6: scenario engine (FR-13, FR-14, FR-15)

**Code:** `src/scenarios.py`

- **Scenarios (FR-13):** `low`, `median` and `high` are the lowest, median and highest national release
  totals in FY2015–FY2025, from `data/processed/releases_by_fy_geo.parquet`. Record which fiscal year each
  one comes from.
- **Simulation (FR-14):** draw shares from the Week 5 model and multiply by each scenario's national
  total. Report the mean of the draws as the expected value, and the 10th and 90th percentiles as the 80%
  range. Until Week 5 is validated, "last year's shares" with an error model is the BRD's allowed
  fallback (risk R-03). Say which one you used in `share_model`.
- **Calibration (FR-14, NFR-10):** for each held-out year FY2018–FY2025, simulate from earlier years
  only, using that year's actual national total. Count how many states, and how many listed counties,
  landed inside their 80% range. Pooled over the years, this should be about 80%; the test accepts
  70%–90%.
- **Service needs (FR-15):** at least `school_age`, from ORR's published age mix. The source is
  [ORR's UAC Age Data](https://acf.gov/orr/data/uac/age), an XLSX file of children in ORR care by age
  (published Oct 7, 2026). Download it yourself and record it in the README's data table.
  - ORR's ages describe children **in care**, not children released. Using them for released children is
    assumption A-03, so say so in the measure's definition.
  - ORR groups ages 0–12 together, so say which age groups you count as school-age.
  - Optional extra measures, each needing a label and a definition:
    - post-release services referrals: [ORR post-release services](https://acf.gov/orr/data/uac-post-release-services)
    - primary language: [ORR primary language](https://acf.gov/orr/data/UAC-Primary-Language)
- **Guardrail (FR-19, NFR-03):**
  - A county gets its own row only if it has a published MPI count in some year from FY2015 to FY2025,
    and its expected releases in that scenario are 50 or more.
  - Everything else in the state goes into one "other counties" row.
  - Round every figure to whole children.

**Writes three files to `results/`:**

`scenarios.json`:

```json
{
  "base_fiscal_year": 2025,
  "share_model": "Dirichlet-multinomial (Week 5)",
  "draws": 10000,
  "seed": 20261101,
  "range": [0.1, 0.9],
  "scenarios": [
    {"id": "low", "label": "Low", "national_releases": 0, "source_fiscal_year": 0},
    {"id": "median", "label": "Median", "national_releases": 0, "source_fiscal_year": 0},
    {"id": "high", "label": "High", "national_releases": 0, "source_fiscal_year": 0}
  ],
  "measures": [
    {"id": "releases", "label": "Children released to sponsors", "definition": "..."},
    {"id": "school_age", "label": "School-age children", "definition": "...which ages, and assumption A-03"}
  ],
  "age_mix_source": "ORR UAC Age Data, FY20xx, downloaded 2026-xx-xx"
}
```

`scenario_releases.csv` has one row per scenario × place × measure:

| Column | Meaning |
|---|---|
| `scenario` | `low`, `median` or `high` |
| `geo_level` | `state`, `county` or `other_counties` |
| `state`, `state_name` | two-letter code and full name |
| `county_key`, `county_fips`, `county_name` | as in the Week 1 table, on county rows (`county_fips` is blank for the four Connecticut counties). On other-counties rows, `county_key` and `county_fips` are blank and `county_name` is `Other counties, ST`. State rows leave all three blank. |
| `measure` | an `id` from `scenarios.json` |
| `expected`, `lower_80`, `upper_80` | mean, 10th and 90th percentile of the draws, whole children |

The state rows must add up to the scenario's national total. In each state, the county rows plus the
other-counties row must add up to the state row. Rounding can be off by up to 1%.

`scenario_calibration.csv` has the columns `fiscal_year, geo_level, places, inside_80, coverage`, with one
row per held-out year for `state` and for `county`.

## What the acceptance tests check

| Test | Requirement |
|---|---|
| Backtest has every held-out year, both levels, and the naive baseline | FR-12 |
| Scores are valid (MAE ≥ 0, log score ≤ 0, nothing missing) | FR-12 |
| Summary compares your model with the naive baseline at both levels | FR-12 |
| Scenario volumes are the lowest, median and highest years, with the right source years | FR-13 |
| The files pass every check in `src/scenario_contract.py` (format, ranges, sums, the 50-release rule) | FR-18, FR-19, NFR-03 |
| Every county shown has a published MPI count in some year | FR-19, NFR-03 |
| Every place has a school-age figure, never more than its releases | FR-15 |
| Pooled 80% coverage is 70%–90% for states and for counties | FR-14, NFR-10 |

The app runs the same contract checks. If your files fail any of them, it shows the problem instead of the
numbers.

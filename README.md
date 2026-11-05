# Where Unaccompanied Children Are Placed

Where unaccompanied children were released to sponsors across U.S. states and counties,
FY2015–FY2025, and what a future rise in national volume would mean for local services
(schools, legal aid, case management). Service planning only.

- Plan of record: [`docs/portfolio_plan_2026-10-20.docx`](docs/portfolio_plan_2026-10-20.docx)
- Problem statement (Week 1, draft for approval): [`docs/problem_statement.md`](docs/problem_statement.md)
- Week 4 findings memo (concentration, stability, geography): [`docs/week4_findings_memo.md`](docs/week4_findings_memo.md)
- Spec for the Week 5 share model and Week 6 scenario engine: [`docs/spec_week5_week6.md`](docs/spec_week5_week6.md)
- Changes: [`CHANGELOG.md`](CHANGELOG.md)

**Status:** Weeks 1–4 done (data assembly, exploratory analysis, concentration and persistence, geography).
Week 2 was reviewed against Week 1 and the BRD on its own: it now runs on Week 1's table alone and includes
the per-year maps. Week 3 was reviewed the same way: county concentration now counts counties one by one
(it had counted all unlisted counties as one place), and Lorenz curves and per-year transition matrices are
added. Week 7 built: the Streamlit app, its tests and a reshaping unit test. The app's History tab
works now. Its Scenario tab waits for the Week 5 share model and Week 6 scenario engine, which the project
owner is writing to [`docs/spec_week5_week6.md`](docs/spec_week5_week6.md). FSO and contract-lead sign-off
is still pending.
This repository is **public** since October 25, 2026, released by the project owner. The alignment notes
with the MP project stay local and unpublished.

## Built alongside another project

This project is being built alongside **[MP](https://github.com/patrickdoyle314/MP)**, a separate
project on open missing-person cases for children and young adults. The two stay separate: each has
its own data, code, README and changelog. They communicate only through aggregate tables under the
shared contract in [`exchange/EXCHANGE.md`](exchange/EXCHANGE.md); no individual records pass between
them, and MP's adult figures never enter this project's comparisons.

## Guardrails

These apply to every file, chart and write-up in this project:

1. **Public, aggregate data only.** No program data, internal knowledge, screenshots, or anything learned on the job.
2. **Service planning only.** Never framed as, or usable as, a tool for locating children, sponsors or households.
3. **Respect ORR's threshold.** Counties with fewer than 50 releases are not published, and their counts are never backed out.
4. **Neutral language.** "Unaccompanied children", "released to sponsors"; describe patterns, not blame.
5. **Counts are service needs,** not characteristics of the communities.

## Layout

```
UC-Placement/
  README.md, CHANGELOG.md
  docs/                 plan of record (.docx, kept local), problem statement, Week 4 memo, Week 5-6 spec
  src/build_dataset.py  Week 1: reshape MPI data, add other-counties rows, join Census
  src/measure.py, src/share_baseline.py, src/run_sql.py   Week 3 measures, tiers, share baselines, SQL runner
  src/geography.py, src/build_week4_memo.py              Week 4: Moran's I, LISA, school-age comparison; memo
  src/scenario_contract.py  format and guardrail checks for the scenario engine's files
  app/                  Week 7: Streamlit app (streamlit_app.py) and its glossary (terms.py)
  notebooks/            Week 2 exploratory notebook and its builder (needs only Week 1's table)
  sql/                  SQL statements (DuckDB over parquet)
  results/              aggregate outputs
  tests/                pytest checks; tests/fixtures/ holds synthetic scenario files for the app tests
  data/raw/             downloaded sources (not committed; see Data)
  data/processed/       generated tables (not committed)
  exchange/             contract and export for adjacent projects (see Exchange)
  alignment/            local-only coincidence notes with the MP project (not committed)
```

## Reading the code

Every Python and SQL file from Weeks 1–4 opens with a **HOW TO READ THIS FILE** block: what the file does for the project
(business purpose), how it is laid out, and the Python ideas it uses. Comments through the code explain *why*
each step exists (for example, why "other counties" are never split) and point out Python, pandas and SQL
techniques where they first appear. A suggested reading order for learning Python: `src/build_dataset.py` →
`src/measure.py` (NumPy, pandas) → `sql/state_ranks.sql` (window functions) → `src/share_baseline.py` →
`tests/test_measure.py` (pytest) → `notebooks/build_week2_eda.py`, whose comments also appear inside the
notebook's code cells → `src/geography.py` (GeoPandas, spatial statistics).

## Data

| Source | File | Notes |
|---|---|---|
| [Migration Policy Institute: Released to Sponsors by State and County, FY 2014–2025](https://www.migrationpolicy.org/data-tool/unaccompanied-children-state-county) | `data/raw/mpi/mpi-data-hub_uacsbystate-county-fy2014-fy2025.xlsx` (133,945 bytes, downloaded 2026-10-22) | Tabulation of ACF/ORR data. Counties listed only for years with ≥ 50 releases. First release location only. Includes FY2014, Puerto Rico and the U.S. Virgin Islands. |
| [Census Bureau Vintage 2024 county estimates by age and sex](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/) | `data/raw/census/cc-est2024-agesex-all.csv` (8,723,627 bytes, downloaded 2026-10-22) | County FIPS codes; July 1, 2024 total and ages 5–17 population. Covers the 50 states and DC only. |
| Census ACS 5-year (language spoken at home) | — | Pending: needs a free Census API key, which you request yourself at api.census.gov. |
| [Census 2023 cartographic boundary files](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) (1:20,000,000) | `data/raw/geo/cb_2023_us_state_20m.zip`, `cb_2023_us_county_20m.zip` | State and county shapes for the maps and the app. |

### Fiscal-year alignment

Every figure is placed on the federal fiscal year (October 1 – September 30):

| Source | Its own period | How it is aligned |
|---|---|---|
| MPI release counts | Federal fiscal year | Used as published. FY2015–FY2025 are analyzed; FY2014 stays in the Week 1 table only. |
| Census Vintage 2024 estimates | July 1, 2024 (inside FY2024) | One fixed reference population for every fiscal year, not re-estimated year by year. |
| Census ACS 5-year (pending) | A five-calendar-year period | To be used the same way: a fixed reference, labeled with its period. |
| ORR age data (Week 6) | Federal fiscal year | The engine uses the fiscal year it names in `results/scenarios.json`. |
| CBP encounters (optional, not used) | Monthly | Would be summed October through September. |

## Run

```bash
pip install -r requirements.txt   # SciPy, libpysal + esda (spatial statistics), matplotlib and python-docx (reporting)
python src/build_dataset.py          # Week 1 table + reconciliation
python notebooks/build_week2_eda.py  # Week 2 notebook and its charts, including maps for every year
python src/measure.py                # Week 3: concentration, Lorenz curves, persistence, tiers
python src/share_baseline.py         # Week 3: share baselines and their backtest
python src/run_sql.py                # Week 3: state ranks in SQL (DuckDB)
python src/geography.py              # Week 4: Moran's I, LISA, school-age comparison (after src/measure.py)
python src/build_week4_memo.py       # Week 4 findings memo, from the results tables
streamlit run app/streamlit_app.py   # Week 7: the scenario app, in your browser
python exchange/export_exchange.py   # aggregates for adjacent projects
python alignment/align_mp.py         # optional, local only: coincidence checks with MP
```

## Measures, model and SQL

| Path | What it is |
|---|---|
| `src/measure.py` | pandas + NumPy: concentration (HHI, effective number, Gini, top-10 share, Lorenz) and persistence (Spearman, Kendall) by fiscal year; county size tiers and their Markov transition matrix; writes the parquet table |
| `src/geography.py` | GeoPandas + libpysal + esda: global Moran's I and LISA clusters (states: releases per school-age child; counties: years listed), Moran's I by year, release share vs school-age share |
| `src/build_week4_memo.py` | Writes `docs/week4_findings_memo.md` from the results tables, with the tier transition chart |
| `src/share_baseline.py` | Share model, baseline stage: next year's state shares from last year, a 3-year mean, or all years pooled, backtested |
| `docs/MODEL_CARD_share_model.md` | Model card: data, baselines and scores, the planned Bayesian model, limitations |
| `sql/state_ranks.sql` | SQL with CTEs and window functions (`RANK`, `LAG`, running `SUM`) over the parquet table |
| `src/run_sql.py` | Runs a SQL file with DuckDB, saves the result in `results/` |
| `src/scenario_contract.py` | What the scenario engine's files must contain, and the checks the app runs before showing them |
| `app/streamlit_app.py` | Streamlit + Plotly app: scenario selector, state and county maps, tables with 80% ranges, history, definitions |
| `tests/` | pytest: metric checks, the reshaping step on made-up counties, reconciliation, SQL matches pandas, tiers, Moran's I, clusters, school-age ratio, the Week 2 notebook's BRD checks, county concentration bounds and Week 3's BRD checks, the app (Streamlit's AppTest), and acceptance tests for Weeks 5–6 that skip until those outputs exist |
| `results/` | Outputs (aggregate, from public MPI data) |

```bash
python src/measure.py
python src/share_baseline.py
python src/run_sql.py
python src/geography.py
python src/build_week4_memo.py
python -m pytest
```

## Week 7: the scenario app

`streamlit run app/streamlit_app.py` opens the app in a browser. A planner picks a national volume scenario (Low,
Median or High, each one a real year's national total from FY2015–FY2025) and a state. The app then shows:

- **Scenario:** state and county maps of expected releases or school-age children, and sortable tables with the
  expected value and the 80% range for every state, listed county and state "other counties" figure. It also
  shows how often the ranges held the actual figure in backtests.
- **History:** published counts for any fiscal year on state and county maps, the national or state trend, and
  how many of the 11 years each county was listed (steady or changing need).
- **Definitions:** a plain-language glossary. Every table column also has its own help text.
- **About and guardrails:** purpose, guardrails, limits, and how the app was built.

Guardrails are enforced in code, not only stated:

- The app runs `src/scenario_contract.py` on the scenario files before drawing anything. If a check fails, for
  example a county with fewer than 50 expected releases shown by itself, the app shows the problem instead of
  the numbers.
- The History tab shades a county only in years it was published (50+ releases).

The tests run the app on synthetic scenario files in `tests/fixtures/scenarios/`, which are made up and describe
nothing real. They check that:

- choosing a scenario refreshes every table;
- no county under 50 is shown by itself;
- every column is defined;
- files that fail the checks are not shown.

The same per-year maps are saved as images by the Week 2 notebook (see Week 2 results).

## Week 4 results: geography

Full memo with charts and methods: [`docs/week4_findings_memo.md`](docs/week4_findings_memo.md). Check-in question:
*is the pattern stable enough that last year predicts next year?*

1. **States, yes.** Year-to-year state rank correlations are 0.985 or higher, and "last year's shares" misses each
   state's share by 0.21 percentage points on average, the best of three simple rules.
2. **Counties: steady places, moving counts.** How many counties clear the 50-release threshold follows national
   volume (73 listed in FY2020, 338 in FY2022, 109 in FY2025); a 1,000+ county stays 1,000+ the next year 58% of the time.
3. **Releases cluster.** Moran's I is 0.48 for state release rates per school-age child and 0.40 for how often
   counties are listed (both p = 0.0001), and every single year is significant. Eight county clusters (the largest
   runs from Prince George's County, MD to Suffolk County, NY) received 51% of all FY2015–FY2025 releases.
4. **Compared with school-age population,** listed counties took 1.4–2.0 times their share each year. The 70
   counties listed every year received 59% of releases and have 31% of the nation's school-age children.

## Week 3 results: concentration and persistence

`src/measure.py` (pandas, NumPy) reads only Week 1's table and writes its tables to `results/` for every fiscal
year (BRD FR-07, FR-08). The **effective number** (1 / HHI) reads "as concentrated as if releases were spread
evenly over this many places": higher means more spread out.

| Fiscal year | States: effective number | States: top-10 share | Listed counties | Counties: effective number (at least) | Counties: top-10 share | Unlisted counties' share |
|---|---|---|---|---|---|---|
| FY2015 | 14.7 | 72% | 108 | 71 | 29% | 27% |
| FY2016 | 13.5 | 75% | 156 | 60 | 33% | 18% |
| FY2017 | 13.6 | 74% | 138 | 64 | 31% | 20% |
| FY2018 | 14.9 | 70% | 124 | 82 | 26% | 27% |
| FY2019 | 14.8 | 72% | 226 | 76 | 27% | 15% |
| FY2020 | 14.5 | 71% | 73 | 76 | 26% | 36% |
| FY2021 | 15.6 | 70% | 298 | 88 | 24% | 12% |
| FY2022 | 15.3 | 69% | 338 | 88 | 24% | 11% |
| FY2023 | 16.4 | 67% | 334 | 107 | 22% | 12% |
| FY2024 | 17.3 | 64% | 322 | 132 | 19% | 15% |
| FY2025 | 16.5 | 65% | 109 | 112 | 21% | 35% |

1. **Concentration** (`concentration_by_year.csv`, Lorenz curves in `lorenz_by_year.csv` and
   [`results/figures/week3_lorenz.png`](results/figures/week3_lorenz.png)). Releases are concentrated, and the
   concentration has eased slowly for both states and counties. The Gini coefficient is 0.61–0.69 for states
   and 0.39–0.61 among listed counties.
   - **States:** the largest fifth of states received 64%–76% of children each year, and the smaller half 7%–10%.
   - **Counties:** the county curves and Gini cover listed counties only, and the number listed swings with
     volume. They look flattest in FY2020 and FY2025, when only 73 and 109 counties reached 50 releases and
     the listed set held only larger counties. So compare county curves across years with care, and use the
     effective numbers above for trends.
2. **How counties are counted.** Counties under 50 releases are not published, and they are never split or
   estimated. Each of them had at most 49 releases, which limits how much they can add, so county HHI is a
   narrow range (`hhi_low` to `hhi`). The effective numbers above are the low end of that range. The ten largest
   counties are always listed, so their share is exact.
3. **Persistence** (`persistence_state_ranks.csv`, `persistence_county_ranks.csv`). Year-to-year rank
   correlations of state shares are Spearman 0.985–0.996 and Kendall 0.910–0.962. Among the 73–310 counties
   published in both years of a pair, they are Spearman 0.877–0.968 and Kendall 0.699–0.857.
4. **Tiers** (`tier_transitions.csv` pooled; `tier_transitions_by_year.csv` for each pair of years). A county
   with 1,000+ releases stays 1,000+ the next year 58% of the time; one with 50–199 falls below the threshold 34%
   of the time.

## Week 2 results: exploratory analysis

[`notebooks/week2_eda.ipynb`](notebooks/week2_eda.ipynb), built and run by `notebooks/build_week2_eda.py` (pandas,
matplotlib, GeoPandas with Census 2023 cartographic boundaries). Charts are also in `results/figures/week2_*.png`.
It reads only Week 1's table and the raw boundary files, so it runs right after `src/build_dataset.py`.

**Review question:** do county rows plus "other counties" match each state total? Yes. The notebook checks
this again before any finding: all 583 state-years in FY2015–FY2025 match (50 states, DC, Puerto Rico, the
Virgin Islands), and states add up to the national total in all 11 years.

Five findings, FY2015–FY2025 (BRD FR-05):

1. National releases ranged from 16,864 (FY2020) to 127,512 (FY2022); FY2021–FY2024 hold 62% of all releases, and
   FY2025 fell to 24,259, 76% below FY2024.
2. The six largest receiving states (TX, CA, FL, NY, MD, NJ) took 53% of releases; Texas's share stayed between
   11.7% and 14.9%, and year-to-year state rank correlations never fell below 0.985 (FY2017 to FY2018).
3. The 20 largest receiving counties took 34% of releases; Harris County, TX received the most children in 9 of
   11 years, and all 20 were listed (50+ releases) every year.
4. Listed counties ranged from 73 (FY2020) to 338 (FY2022) and held 63%–89% of releases; the rest are the
   unlisted "other counties" group, never split further.
5. Per school-age child (ages 5–17, 2024), the highest totals were in Maryland, DC and Virginia (36 per 1,000) and
   the lowest in Hawaii, Vermont and Alaska. 389 of the 393 listed counties are on the county map (4 Connecticut
   counties have no FIPS match; Alaska, Hawaii and Puerto Rico are left off the maps).

State and county maps for every fiscal year, on one shared color scale (BRD FR-06):
[`results/figures/week2_state_maps_by_year.png`](results/figures/week2_state_maps_by_year.png) and
[`results/figures/week2_county_maps_by_year.png`](results/figures/week2_county_maps_by_year.png). County panels
shade only published counts (50+ releases).

## Week 1 results

`src/build_dataset.py` writes:

- **`data/processed/releases_by_fy_geo.csv`**: 3,673 rows, one per fiscal year × geography:
  12 national, 636 state (50 states, DC, PR, VI), 2,389 county, 636 "other counties".
  Columns: `fiscal_year, geo_level, state, state_name, county_fips, county_name, county_key, releases,
  listed_counties, pop_total_2024, pop_5_17_2024`.
- **`data/processed/reconciliation.csv`**: 648 checks, **all pass**. For every state and year, listed
  counties plus "other counties" equal the state total. For every year, states sum to the national total.
- **`data/processed/county_fips_unmatched.csv`**: 389 of 393 MPI counties matched to a FIPS code. The 4
  unmatched are Connecticut counties (Fairfield, Hartford, New Haven, New London): since 2022 the Census
  reports Connecticut by planning region, not county.

Findings for the plan:

- The MPI file **includes FY2014** (53,515 releases); the plan's data table lists it as unavailable.
- MPI's national totals include Puerto Rico and the U.S. Virgin Islands (together 0–9 releases a year, none
  in FY2014–FY2016 or FY2021); both are kept as state-level rows so the totals reconcile.
- 15 state-year cells are blank in MPI's States sheet (Alaska FY2018 and FY2020, Montana FY2019, Vermont
  FY2017, Puerto Rico in 4 years, the Virgin Islands in 7). They count as 0 releases, as in MPI's own
  FY 2014–2025 total column; read that way, the states add up to the national total in every year.
- Census population is one reference year (July 1, 2024) on every row. Puerto Rico and the Virgin Islands
  have no population in this file.
- The plan says to join ACS county data. Total and school-age population come from the Vintage 2024
  estimates above, which need no API key; the ACS join (language spoken at home) is pending (see Data).

## Limitations

- **First release location only.** A child is counted in the county where they were first released to a
  sponsor; later moves are not tracked.
- **Small counties are not published.** Counties with fewer than 50 releases in a year appear only inside their
  state's "other counties" figure, and nothing is estimated for them. Every county-level result therefore covers
  listed counties only, which leans toward large counties. A methods note on this is an optional item, not yet
  written.
- **One reference population.** Every year uses the July 1, 2024 Census estimates. Puerto Rico and the Virgin
  Islands have none in that file.
- **Connecticut.** Its four listed counties have no current Census FIPS code (the Census now reports Connecticut
  by planning region), so they have no population and are not drawn on maps. They do appear in tables.
- **Scenarios are not forecasts.** Low, Median and High are past national totals. The scenario engine assumes
  the historical pattern of where children are released holds at those volumes; if it shifts, the ranges will be
  too narrow.
- **Service needs are approximate.** School-age figures will use ORR's national age mix for children in its care,
  which may differ from the children released to a given place.
- **Language spoken at home** (ACS) is not yet included.
- **Source revisions.** MPI and ORR can revise published figures. Each downloaded file is listed above with its
  date.

## How this was built

The project owner set the question, scope, guardrails and tools, and reviewed the results. Most of the code for
Weeks 1–4 and Week 7 was written with AI assistance (Claude, by Anthropic): data assembly, measures, geography,
maps, the app and the tests. This section, not the commit history, records which parts are which. The project owner writes the
Week 5 share model, the Week 6 scenario engine and the written summary. AI assistance on those parts is limited
to the spec and acceptance tests ([`docs/spec_week5_week6.md`](docs/spec_week5_week6.md),
`tests/test_acceptance.py`), step-by-step guidance (what each step is for, the choices it involves, and how to
check it, without code), and code review.

## Exchange with adjacent projects

This project and the MP project (missing children and young adults, `../MP`) are **separate
projects that share aggregates only**, through the contract in
[`exchange/EXCHANGE.md`](exchange/EXCHANGE.md) (v1.0). Each writes `exchange/outbox/` and reads the
other's; no raw records cross. From MP, only **child** measures are used. Adult measures
(ages 18–25) are kept apart and never enter child comparisons.

## Alignment notes (local only)

`alignment/` holds the coincidence log between the two projects
([`alignment/README.md`](alignment/README.md)) and the script that produces it. It is excluded through
`.git/info/exclude` and is not part of this project's deliverables until sign-off covers it.

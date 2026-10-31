# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
dates are when the change was made.

## [Unreleased]

### Changed
- README Week 3 results: what the Lorenz curves show, and why county curves (listed counties only) should be
  compared across years with care. In FY2020 and FY2025 only 73 and 109 counties were listed.

## [0.6.2] - 2026-10-31 (Week 3 review)

Week 3 checked on its own against Weeks 1–2 and the BRD (FR-07, FR-08, NFR-03, NFR-07, NFR-08). Week 4 was not
reviewed. Its memo's county bullet was rewritten because it depended on the Week 3 error fixed below.

### Fixed
- **County concentration counted every unlisted county in the nation as one place.**
  - That one "place" held 11%–37% of releases, so it drove the county HHI, effective number and top-10 share.
  - The old figures were 7–44 effective places, with the lump among the "top 10". They measured how many
    children fell below the threshold, not how concentrated counties are.
  - Counties are now counted one by one, and no unlisted county is split or estimated. Each unlisted county had
    at most 49 releases, so county HHI is a narrow range: `hhi_low` to `hhi`.
  - Corrected figures: 60–132 effective counties; the top 10 counties took 19%–33%.
  - Gini is now among the listed counties.
  - State figures are unchanged.
- FR-07 asks for Lorenz curves. `lorenz()` existed but nothing used it. Now written:
  - `results/lorenz_by_year.csv`
  - `results/figures/week3_lorenz.png`
- FR-08 asks for a transition matrix for every consecutive year pair. Only the pooled matrix was written. Added
  `results/tier_transitions_by_year.csv`.
- The README's main Run steps skipped Week 3. Week 4 needs Week 3's parquet table, so a clean run in that order
  failed. The Week 3 steps are now included.

### Added
- `results/persistence_county_ranks.csv`: Spearman and Kendall rank correlations for counties published in both
  years of each pair (FR-08).
- `concentration_by_year.csv` columns: `hhi_low`, `effective_n_high`, `unlisted_share`. HHI is now rounded to
  5 decimals.
- README "Week 3 results": every year's figures, with how to read them.
- `tests/test_week3.py`: 10 checks.
  - The county HHI range holds the true value however the unlisted counties are split.
  - The unlisted group never counts as one county.
  - One transition matrix per year pair.
  - Every year and year pair is present in the results (FR-07, FR-08).

### Changed
- `src/build_week4_memo.py` and `docs/week4_findings_memo.md`: the county concentration bullet. Nothing else in
  Week 4 changed; its other results are byte-identical.

### Notes
- All 23 Python files compile, with warnings treated as errors.
- The whole pipeline was run in a fresh copy of this commit, with only the raw downloads added:
  - every step in the README's Run order exits cleanly;
  - the app starts and answers its health check;
  - 45 tests pass and 8 skip;
  - all 36 regenerated tables, the charts, the memo and the notebook outputs are byte-identical to the
    committed ones.

## [0.6.1] - 2026-10-31 (Week 2 review)

Week 2 checked on its own against Week 1 and the BRD, as v0.5.1 did for Week 1. The BRD items covered are
FR-05, FR-06, NFR-03, NFR-04, NFR-12 and the Week 2 review question.

### Fixed
- `notebooks/build_week2_eda.py` used to read two Week 3 outputs from `src/measure.py`: the parquet copy and the
  persistence table. A clean install run in the README's order (Week 1, then Week 2) failed.
  - It now reads Week 1's CSV.
  - It computes the state rank correlations itself, with the same result as Week 3 (0.985, FY2017 to FY2018).
- The notebook did not answer the Week 2 review question. Before any finding it now checks that:
  - listed counties plus "other counties" equal each state total (583 of 583 state-years);
  - states add up to the national total (11 of 11 years).
  The notebook stops if either check fails.
- Chart labels (NFR-12):
  - The state-share axis said "national releases", but the shares are of the 50 states and DC, as in Weeks 3–4.
  - The top-20 heatmap now says that a blank cell means under 50 and not published.
  - The state map defines school-age as ages 5–17.
- Finding 4's heading said "surge years". It now says "higher-volume years" (NFR-04, neutral language).

### Moved
- The per-year state and county maps (FR-06) moved into the Week 2 notebook. Before, they were made by
  `src/maps_by_year.py` (v0.6.0), which needed Week 4 code. The script and the `week7_*` images are removed.
  - `results/figures/week2_state_maps_by_year.png`
  - `results/figures/week2_county_maps_by_year.png`

### Added
- `tests/test_week2.py`: 4 checks on the saved notebook.
  - Five findings, each with a chart (FR-05).
  - Maps for every year (FR-06).
  - The reconciliation check ran and passed.
  - The builder reads only Week 1's table and the raw boundary files.

### Notes
- The five finding sentences are unchanged except finding 2: it now gives the correlation to three decimals
  (0.985; it was "0.98").
- Three charts are byte-identical; three changed only in their labels.
- 36 tests pass; 8 acceptance tests skip until Weeks 5–6 are built.

## [0.6.0] - 2026-10-31 (Week 7: app and tests; spec for Weeks 5–6)

Work is now split with the project owner: the owner writes the Week 5 share model, the Week 6 scenario engine
and the written summary; this release adds what those plug into. Week 5 code is untouched.

### Added
- `app/streamlit_app.py`, `app/terms.py`: Streamlit + Plotly app (BRD FR-16 to FR-20).
  - Scenario selector; state and county maps; sortable tables with expected value and 80% range for every
    state, listed county and "other counties" figure; backtest coverage of the ranges.
  - History tab: published counts by year on maps, trends, years listed per county.
  - A plain-language glossary, and help text on every column.
  - The Scenario tab says the tables are not built yet until the engine's files exist.
- `src/scenario_contract.py`: the format of the scenario engine's three files and the checks run on them.
  Format, ranges, sums, and the 50-release rule: a county appears by itself only with 50+ expected releases.
  The app shows nothing from files that fail.
- `docs/spec_week5_week6.md`: what the owner's share model and scenario engine must produce. It points to
  ORR's age data (children in care, XLSX) for the school-age measure.
- `tests/test_acceptance.py`: 8 acceptance tests for Weeks 5–6, mapped to FR-12 to FR-15, FR-19, NFR-03 and
  NFR-10. They skip until the owner's outputs exist.
- `tests/test_app.py`: 13 tests.
  - The checks catch each kind of problem.
  - The app offers three scenarios; choosing one refreshes the tables.
  - No county under 50 is shown by itself; every column is defined; failing files are not shown.
  - They run on synthetic files from `tests/fixtures/make_scenario_fixture.py`.
- `tests/test_build_dataset.py`: 6 unit tests of the reshaping step on made-up counties (NFR-08).
  - One row per year and place; unpublished cells get no row; FIPS and key are carried.
  - Other counties = state minus listed, with population left blank when a county is unmatched.
  - Reconciliation flags counties above their state total.
- `src/maps_by_year.py`: state and county maps for every fiscal year, FY2015–FY2025, on a shared scale (FR-06).
  - `results/figures/week7_state_maps_by_year.png`
  - `results/figures/week7_county_maps_by_year.png`
- README sections:
  - Fiscal-year alignment for every source (FR-04).
  - Week 7 app.
  - Limitations (NFR-09).
  - How this was built: which parts are AI-assisted and which the owner writes.
- `requirements.txt`: streamlit, plotly.

### Changed
- `src/build_dataset.py`: the reshaping step moved out of `main()` into `reshape()`, which reads and writes no
  files, so it can be unit-tested. The three Week 1 CSV files are byte-identical.

### Notes
- 32 tests pass; 8 acceptance tests skip until Weeks 5–6 are built.
- New code uses shorter comments than the Weeks 1–4 HOW TO READ blocks.

## [0.5.1] - 2026-10-27 (Week 1 review)

### Fixed
- README Week 1 results said Puerto Rico and the Virgin Islands had 1–9 releases a year; together they had
  0–9, with none in FY2014–FY2016 or FY2021.
- `src/build_dataset.py`: two comments broken across lines mid-sentence, and a comment that named only the
  Virgin Islands as missing from the Census county file (Puerto Rico is missing too).

### Changed
- `src/build_dataset.py` comments: a Layout part in HOW TO READ THIS FILE; why a blank MPI state cell counts
  as 0 releases (MPI's own total column does the same); why Connecticut's "other counties" population stays
  blank; long end-of-line comments moved to their own lines. Comments only: the syntax tree matches v0.5.0,
  and the three Week 1 CSV files are byte-identical.
- README Data table gives the Census file's size and download date. Week 1 findings add the 15 blank state
  cells and note that population comes from the Vintage 2024 estimates while the ACS join is pending.

### Notes
- Week 1 checked against the plan of record: `python src/build_dataset.py` gives 3,673 rows, 648 of 648
  reconciliation checks pass, and the 4 Connecticut counties are the only FIPS misses; 13 tests pass.
- Still pending: FSO and contract-lead approval of the problem statement; ACS language data (needs a Census
  API key); a Connecticut county-to-planning-region crosswalk, which would change Week 2 and Week 4 county
  counts.

## [0.5.0] - 2026-10-26 (Week 4: geography)

### Added
- `src/geography.py`: global Moran's I and local clusters (LISA) for states (releases per 1,000 school-age
  children) and counties (years listed with 50+ releases, a published fact only), Moran's I for each fiscal
  year, neighboring High-High counties grouped into named clusters, false-discovery-rate counts, and release
  shares compared with school-age population shares (listed counties, other counties as one group, and the
  70 counties listed every year). Tables in `results/`, charts in `results/figures/week4_*.png`.
- `src/build_week4_memo.py` and `docs/week4_findings_memo.md`: the Week 4 findings memo on concentration,
  stability and geography, with every number read from `results/`. It answers the check-in question: state
  shares are stable enough that last year predicts next year; county counts move with national volume.
- County size tiers and their Markov transition matrix in `src/measure.py` (`results/tier_transitions.csv`,
  `results/county_tiers_by_year.csv`): the Week 3 plan item that had not been built yet.
- `tests/test_geography.py`: tiers, Moran's I on known patterns, cluster grouping, the school-age ratio, and a
  check that tier counts match the published county rows (13 tests in all).
- `esda` in `requirements.txt`.

### Notes
- With 49 states, no single state cluster passes the false-discovery-rate correction; the memo calls them
  suggestive. 105 of 151 High-High counties pass it.
- Connecticut's four listed counties are left out of the county map statistics (its 2023 Census counties are
  planning regions).

## [0.4.2] - 2026-10-26

### Changed
- Comments for readers learning Python: every Python and SQL file now opens with a "HOW TO READ THIS FILE"
  block (business purpose, layout, Python ideas used), with notes through the code on why each step exists
  and which Python, pandas or SQL technique it uses. README gains a "Reading the code" section.
- The notebook builder's comments also appear inside the notebook's code cells; `notebooks/week2_eda.ipynb`
  was regenerated with identical outputs and byte-identical figures.
- Comments and docstrings only: syntax trees match the previous version file by file (notebook cell code
  included; SQL compared without comments); tests pass.

## [0.4.1] - 2026-10-25

### Changed
- Repository made public on GitHub at the project owner's direction (was private pending sign-off).
  README and problem statement status updated; the alignment notes with MP stay local and unpublished.

## [0.4.0] - 2026-10-25 (Week 2: exploratory analysis)

### Added
- `notebooks/week2_eda.ipynb`: five findings, each with a chart (national releases by year, top state shares,
  top 20 counties over time, listed vs other counties, state and county maps); outputs saved in the notebook.
- `notebooks/build_week2_eda.py`: builds and runs the notebook so it stays reproducible.
- `results/figures/week2_*.png`: the notebook's charts.
- `data/raw/geo/`: Census Bureau 2023 cartographic boundary files (states and counties, 1:20m), not committed.
- `requirements.txt`: GeoPandas, and nbformat / nbclient / ipykernel for building the notebook.

### Changed
- README status: Weeks 1–3 done (Week 3 had landed before Week 2).

## [0.3.0] - 2026-10-23

### Added
- `src/measure.py` (pandas + NumPy): concentration (HHI, effective number, Gini, top-10 share, Lorenz) and
  persistence (Spearman, Kendall) by fiscal year; writes the parquet table.
- `src/share_baseline.py`: share model baselines and backtest (last year's shares: 0.212 share points).
- `docs/MODEL_CARD_share_model.md`: model card, including the planned Dirichlet-multinomial model.
- `sql/state_ranks.sql`: CTEs and window functions (`RANK`, `LAG`, running `SUM`) over parquet with DuckDB;
  `src/run_sql.py` runs it.
- `tests/`: pytest checks (metrics, reconciliation, SQL matches pandas).
- `results/`: aggregate outputs.
- `requirements.txt`: pandas, pyarrow, DuckDB, pytest.

## [0.2.1] - 2026-10-22

### Added
- `requirements.txt`, including `matplotlib` and `python-docx` for reporting, `scipy` for analysis and backtests,
  and `libpysal` for spatial weights (Week 4 Moran's I and LISA; brings in `geopandas`, `shapely`, `pandas`).

## [0.2.0] - 2026-10-22

### Added
- `docs/modeling_candidates.md`: ranked predictive candidates for service planning.
- `src/probes/share_backtest.py`: how predictable next year's state and county shares are (last year's shares: 0.206 share-point error at state level).

## [0.1.1] - 2026-10-22

### Added
- Private GitHub repository (github.com/patrickdoyle314/UC-Placement); public only after FSO and
  contract-lead sign-off.
- README section "Built alongside another project", linking to the MP repository.

### Changed
- README and problem statement status: private on GitHub instead of local only.

## [0.1.0] - 2026-10-22 (Week 1: scope and data assembly)

### Added
- Project folder, separate from the MP project and adjacent to it (`../MP`).
- `docs/portfolio_plan_2026-10-20.docx`: plan of record.
- `docs/problem_statement.md`: one-page problem statement, draft for FSO and contract-lead review.
- `data/raw/mpi/`: MPI release file, FY2014–FY2025 (133,945 bytes, downloaded 2026-10-22).
- `data/raw/census/cc-est2024-agesex-all.csv`: Census Vintage 2024 county population by age.
- `src/build_dataset.py`: one row per fiscal year × geography, keyed by county FIPS; "other counties"
  row per state; Census total and ages 5–17 population joined; reconciliation and unmatched-county reports.
- `exchange/` (contract v1.0, same core as MP's) and `exchange/export_exchange.py`.
- `alignment/align_mp.py`: coincidence checks that read only the two exchange outboxes and use MP's
  child measures only. Local only.

### Moved
- From MP: the MPI file (was `MP/data/mpi/`) and the alignment notes (was `MP/alignment/`).
  The old MP alignment script, which read MP's person-level table, is replaced by `alignment/align_mp.py`.

### Found
- 648 of 648 reconciliation checks pass once Puerto Rico and the U.S. Virgin Islands are included.
- 4 Connecticut counties have no FIPS match (Census uses planning regions since 2022).
- The MPI file includes FY2014, which the plan lists as unavailable.

### Pending
- FSO and contract-lead approval of the problem statement.
- ACS language-spoken-at-home join (needs a Census API key).
- Connecticut county-to-planning-region crosswalk.

"""Acceptance tests for the owner's Week 5 share model and Week 6 scenario engine.

Each test is skipped until the output it checks exists (see docs/spec_week5_week6.md).
"""
from pathlib import Path

import pandas as pd
import pytest

from src import measure
from src import scenario_contract as sc

ROOT = Path(__file__).resolve().parent.parent
BACKTEST = ROOT / "results/share_model_backtest.csv"
SUMMARY = ROOT / "results/share_model_summary.csv"
HELD_OUT = range(2018, 2026)
LEVELS = ("state", "county")

week5 = pytest.mark.skipif(not BACKTEST.exists() or not SUMMARY.exists(),
                           reason="Week 5 output not built yet (src/share_model.py)")
week6 = pytest.mark.skipif(not sc.available(), reason="Week 6 output not built yet (src/scenarios.py)")
needs_data = pytest.mark.skipif(not (ROOT / "data/processed/releases_by_fy_geo.parquet").exists(),
                                reason="run src/build_dataset.py and src/measure.py first")


@week5
def test_backtest_has_every_held_out_year_and_the_baseline():  # FR-12
    bt = pd.read_csv(BACKTEST)
    for level in LEVELS:
        for fy in HELD_OUT:
            methods = set(bt[(bt.level == level) & (bt.fiscal_year == fy)].method)
            assert "naive" in methods and len(methods) >= 2, (level, fy, methods)


@week5
def test_backtest_scores_are_valid():  # FR-12
    bt = pd.read_csv(BACKTEST)
    assert bt[["mae_share_points", "log_score"]].notna().all().all()
    assert (bt.mae_share_points >= 0).all() and (bt.log_score <= 0).all()


@week5
def test_summary_compares_the_model_with_naive():  # FR-12
    summary = pd.read_csv(SUMMARY)
    for level in LEVELS:
        methods = set(summary[summary.level == level].method)
        assert "naive" in methods and len(methods) >= 2, (level, methods)


@week6
@needs_data
def test_scenarios_are_the_lowest_median_and_highest_years():  # FR-13
    df = measure.load()
    national = df[(df.geo_level == "national") & df.fiscal_year.isin(measure.FISCAL_YEARS)]
    national = national.set_index("fiscal_year").releases
    target = {"low": national.min(), "median": national.median(), "high": national.max()}
    manifest, _, _ = sc.load()
    for s in manifest["scenarios"]:
        assert s["national_releases"] == target[s["id"]]
        assert national[s["source_fiscal_year"]] == s["national_releases"]


@week6
def test_outputs_pass_the_contract_checks():  # FR-18, FR-19, NFR-03
    assert sc.problems(*sc.load()) == []


@week6
@needs_data
def test_only_published_counties_appear():  # FR-19, NFR-03
    df = measure.load()
    published = set(df[(df.geo_level == "county") & df.fiscal_year.isin(measure.FISCAL_YEARS)].county_key)
    _, table, _ = sc.load()
    shown = set(table[table.geo_level == "county"].county_key)
    assert shown <= published, sorted(shown - published)[:5]


@week6
def test_every_place_has_a_school_age_figure():  # FR-15
    _, table, _ = sc.load()
    places = table.assign(county_key=table.county_key.fillna(""))
    per_place = places.groupby(["scenario", "geo_level", "state", "county_key"]).measure.agg(set)
    assert per_place.apply(lambda m: {"releases", "school_age"} <= m).all()


@week6
def test_80_percent_ranges_cover_about_80_percent():  # FR-14, NFR-10
    _, _, calibration = sc.load()
    assert set(HELD_OUT) <= set(calibration.fiscal_year)
    cover = sc.coverage(calibration)
    for level in LEVELS:
        assert 0.70 <= cover[level] <= 0.90, (level, cover[level])

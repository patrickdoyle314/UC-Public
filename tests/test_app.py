"""Tests for the scenario app and the scenario file checks, run on the synthetic fixture in tests/fixtures."""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.terms import GLOSSARY
from src import scenario_contract as sc

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app/streamlit_app.py"
FIXTURE = ROOT / "tests/fixtures/scenarios"
RELEASES = "Children released to sponsors: expected"


def run_app(folder, monkeypatch) -> AppTest:
    monkeypatch.setenv("UC_RESULTS_DIR", str(folder))
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def scenario_tables(at) -> tuple[pd.DataFrame, pd.DataFrame]:
    states, counties = [d.value for d in at.dataframe if list(d.value.columns)[:1] == ["Place"]]
    return states, counties


def broken_copy(tmp_path, change) -> Path:
    folder = tmp_path / "scenarios"
    shutil.copytree(FIXTURE, folder)
    table = pd.read_csv(folder / sc.TABLE, dtype={"county_key": str, "county_fips": str})
    change(table).to_csv(folder / sc.TABLE, index=False)
    return folder


# --------------------------------------------------------------------------- the checks

def test_fixture_passes_the_checks():
    assert sc.problems(*sc.load(FIXTURE)) == []


def county_under_50(t):
    t.loc[(t.county_key == "harris|TX") & (t.scenario == "low") & (t.measure == "releases"), "expected"] = 30
    return t


def range_out_of_order(t):
    t.loc[0, "lower_80"] = t.loc[0, "expected"] + 1
    return t


def drops_other_counties(t):
    return t[~((t.geo_level == "other_counties") & (t.state == "CA"))]


def states_miss_national(t):
    t.loc[(t.geo_level == "state") & (t.state == "TX"), "expected"] += 500
    return t


def school_age_over_releases(t):
    t.loc[(t.geo_level == "state") & (t.measure == "school_age"), "expected"] *= 3
    return t


@pytest.mark.parametrize("change", [county_under_50, range_out_of_order, drops_other_counties, states_miss_national,
                                    school_age_over_releases])
def test_checks_catch_each_problem(tmp_path, change):
    assert sc.problems(*sc.load(broken_copy(tmp_path, change)))


def test_checks_need_documented_scenarios(tmp_path):
    folder = broken_copy(tmp_path, lambda t: t)
    manifest = json.loads((folder / sc.MANIFEST).read_text())
    manifest["scenarios"] = manifest["scenarios"][:2]
    (folder / sc.MANIFEST).write_text(json.dumps(manifest))
    assert sc.problems(*sc.load(folder))


# --------------------------------------------------------------------------- the app

def test_app_offers_three_scenarios_and_flags_test_data(monkeypatch):
    at = run_app(FIXTURE, monkeypatch)
    assert len(at.radio[0].options) == 3
    assert any("synthetic" in w.value for w in at.warning)


def test_choosing_a_scenario_refreshes_the_tables(monkeypatch):  # FR-16
    at = run_app(FIXTURE, monkeypatch)
    low = scenario_tables(at)[0][RELEASES].sum()
    at.radio[0].set_value("high").run()
    high = scenario_tables(at)[0][RELEASES].sum()
    assert (low, high) == (20000, 120000)


def test_no_county_under_50_is_shown_by_itself(monkeypatch):  # FR-19, NFR-03
    at = run_app(FIXTURE, monkeypatch)
    for scenario in ("low", "median", "high"):
        at.radio[0].set_value(scenario).run()
        counties = scenario_tables(at)[1]
        named = counties[~counties.Place.str.startswith("Other counties")]
        assert (named[RELEASES] >= sc.THRESHOLD).all()
        assert ("Westchester County, NY" in set(named.Place)) == (scenario != "low")


def test_every_column_is_defined(monkeypatch):  # FR-20
    at = run_app(FIXTURE, monkeypatch)
    labels = {m["label"] for m in sc.load(FIXTURE)[0]["measures"]}
    for d in at.dataframe:
        for col in d.value.columns:
            if col in ("Term", "Meaning"):
                continue
            label, _, part = col.partition(": ")
            assert col in GLOSSARY or (label in labels and part.capitalize() in GLOSSARY), col


def test_app_shows_no_figures_from_files_that_fail(tmp_path, monkeypatch):
    at = run_app(broken_copy(tmp_path, county_under_50), monkeypatch)
    assert any("failed the app's checks" in e.value for e in at.error)
    assert not at.radio


def test_app_explains_missing_scenario_files(tmp_path, monkeypatch):
    at = run_app(tmp_path, monkeypatch)
    assert any("not built yet" in i.value for i in at.info)

"""Week 3 checks: county concentration bounds on made-up counties, and BRD FR-07 / FR-08 on the results tables."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import measure

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
YEARS = list(measure.FISCAL_YEARS)


def made_up_counties(listed, unlisted_total):
    rows = [{"fiscal_year": 2015, "county_name": f"c{i}", "releases": v, "listed": True} for i, v in enumerate(listed)]
    rows.append({"fiscal_year": 2015, "county_name": "All other counties", "releases": unlisted_total, "listed": False})
    return pd.DataFrame(rows)


def county_row(listed, unlisted_total):
    states = pd.DataFrame({"fiscal_year": [2015], "state": ["TX"], "releases": [sum(listed) + unlisted_total]})
    conc = measure.concentration(states, made_up_counties(listed, unlisted_total))
    return conc[conc.level == "county"].iloc[0]


@pytest.mark.parametrize("hidden", [[49, 41], [30, 30, 30], [1] * 90])
def test_county_hhi_range_holds_the_true_value(hidden):  # however the unlisted 90 are split, each under 50
    listed = [500, 200, 60]
    row = county_row(listed, sum(hidden))
    every = np.array(listed + hidden, dtype=float)
    true_hhi = np.sum((every / every.sum()) ** 2)
    assert row.hhi_low - 1e-5 <= true_hhi <= row.hhi + 1e-5


def test_unlisted_group_is_never_one_county():
    row = county_row([60], 1000)  # one listed county and a large unlisted group
    assert row.places == 1
    assert row.top10_share == pytest.approx(60 / 1060, abs=1e-3)
    assert row.effective_n > 10  # the 1,000 unlisted children are spread over 21+ counties, not one


def test_no_unlisted_means_exact():
    row = county_row([300, 100], 0)
    assert row.hhi == row.hhi_low == pytest.approx(0.625, abs=1e-5)


def test_transitions_one_matrix_per_year_pair():
    codes = pd.DataFrame({2015: [0, 1, 3], 2016: [1, 1, 2], 2017: [0, 2, 2]}, index=["a", "b", "c"])
    by_year = measure.tier_transitions_by_year(codes)
    assert by_year.groupby(["from_fy", "to_fy"]).counties.sum().to_dict() == {(2015, 2016): 3, (2016, 2017): 3}
    assert len(by_year) == 2 * len(measure.TIERS) ** 2


# --------------------------------------------------------------------------- results tables (FR-07, FR-08)

def test_concentration_every_year_both_levels():
    conc = pd.read_csv(RESULTS / "concentration_by_year.csv")
    for level in ("state", "county"):
        rows = conc[conc.level == level]
        assert sorted(rows.fiscal_year) == YEARS
        assert (rows.hhi_low <= rows.hhi).all() and rows[["gini", "top10_share"]].notna().all().all()


def test_lorenz_curves_every_year_both_levels():
    points = pd.read_csv(RESULTS / "lorenz_by_year.csv")
    ends = points.groupby(["level", "fiscal_year"]).release_share.agg(["first", "last"])
    assert len(ends) == 2 * len(YEARS)
    assert (ends["first"] == 0).all() and np.allclose(ends["last"], 1)
    assert (RESULTS / "figures" / "week3_lorenz.png").exists()


def test_persistence_and_transitions_every_year_pair():
    pairs = list(zip(YEARS[:-1], YEARS[1:]))
    for name in ("persistence_state_ranks.csv", "persistence_county_ranks.csv"):
        table = pd.read_csv(RESULTS / name)
        assert list(zip(table.from_fy, table.to_fy)) == pairs
    by_year = pd.read_csv(RESULTS / "tier_transitions_by_year.csv")
    assert sorted(set(zip(by_year.from_fy, by_year.to_fy))) == pairs
    assert (by_year.groupby(["from_fy", "to_fy"]).size() == len(measure.TIERS) ** 2).all()

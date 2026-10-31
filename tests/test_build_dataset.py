"""Unit tests for the reshaping step (build_dataset.reshape) on a few made-up counties (BRD NFR-08)."""
from src import build_dataset as bd

FYS = bd.FYS
TX_TOTAL = 500


def made_up_inputs(harris_2020=120):
    mpi_states = {name: {fy: None for fy in FYS} for name in bd.USPS}
    mpi_states["Texas"] = {fy: TX_TOTAL for fy in FYS}
    mpi_counties = [
        ("Harris County", "TX", {fy: (harris_2020 if fy == 2020 else 200) for fy in FYS}),
        ("Dallas County", "TX", {fy: (60 if fy == 2020 else None) for fy in FYS}),  # published in one year only
        ("Nowhere County", "TX", {fy: (70 if fy == 2021 else None) for fy in FYS}),  # no Census match
    ]
    census = {("TX", "harris"): ("48201", "Harris County", 1000, 200),
              ("TX", "dallas"): ("48113", "Dallas County", 800, 150)}
    census_states = {"TX": [5000, 1000]}
    us = {fy: TX_TOTAL for fy in FYS}
    return us, mpi_states, mpi_counties, census, census_states


def test_one_row_per_year_and_place():
    rows, _, _, _ = bd.reshape(*made_up_inputs())
    count = lambda level: sum(r["geo_level"] == level for r in rows)
    assert count("national") == len(FYS)
    assert count("state") == count("other_counties") == len(FYS) * len(bd.USPS)
    assert count("county") == len(FYS) + 1 + 1  # Harris every year, Dallas in 2020, Nowhere in 2021


def test_unpublished_cells_get_no_county_row():
    rows, _, _, _ = bd.reshape(*made_up_inputs())
    dallas = [r["fiscal_year"] for r in rows if r.get("county_key") == "dallas|TX"]
    assert dallas == [2020]  # a blank MPI cell is never turned into a 0 or an estimate


def test_county_rows_carry_fips_and_key():
    rows, _, unmatched, _ = bd.reshape(*made_up_inputs())
    harris = next(r for r in rows if r.get("county_key") == "harris|TX")
    assert (harris["county_fips"], harris["county_name"], harris["pop_5_17_2024"]) == ("48201", "Harris County, TX", 200)
    assert unmatched == [("TX", "Nowhere County")]


def test_other_counties_is_state_minus_listed():
    rows, recon, _, _ = bd.reshape(*made_up_inputs())
    other = {r["fiscal_year"]: r["releases"] for r in rows if r["geo_level"] == "other_counties" and r["state"] == "TX"}
    assert other[2019] == TX_TOTAL - 200
    assert other[2020] == TX_TOTAL - 120 - 60
    assert other[2021] == TX_TOTAL - 200 - 70
    assert all(r["ok"] for r in recon)


def test_other_counties_population_left_blank_when_a_county_is_unmatched():
    rows, _, _, _ = bd.reshape(*made_up_inputs())
    other = {r["fiscal_year"]: r for r in rows if r["geo_level"] == "other_counties" and r["state"] == "TX"}
    assert other[2020]["pop_5_17_2024"] == 1000 - 200 - 150
    assert other[2021]["pop_5_17_2024"] == ""  # Nowhere County has no population, so no subtraction


def test_reconciliation_flags_counties_above_the_state_total():
    _, recon, _, _ = bd.reshape(*made_up_inputs(harris_2020=600))
    failed = [(r["fiscal_year"], r["state"]) for r in recon if not r["ok"]]
    assert failed == [(2020, "TX")]

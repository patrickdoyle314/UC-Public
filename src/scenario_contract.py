"""The files the Week 6 scenario engine must write, and the checks run on them before anyone sees them.

The engine itself (src/scenarios.py) is written by the project owner; docs/spec_week5_week6.md explains
the format. The Streamlit app calls problems() and shows nothing from the scenario files if it finds
any, so a guardrail slip (for example a county under 50 releases shown by itself) can't reach a planner.
tests/test_acceptance.py runs the same checks.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
MANIFEST, TABLE, CALIBRATION = "scenarios.json", "scenario_releases.csv", "scenario_calibration.csv"

SCENARIOS = ("low", "median", "high")
GEO_LEVELS = ("state", "county", "other_counties")
REQUIRED_MEASURES = ("releases", "school_age")
COLUMNS = ["scenario", "geo_level", "state", "state_name", "county_key", "county_fips", "county_name",
           "measure", "expected", "lower_80", "upper_80"]
NUMBERS = ["expected", "lower_80", "upper_80"]
CALIBRATION_COLUMNS = ["fiscal_year", "geo_level", "places", "inside_80", "coverage"]
MANIFEST_KEYS = ["base_fiscal_year", "share_model", "draws", "seed", "range", "scenarios", "measures",
                 "age_mix_source"]
THRESHOLD = 50     # ORR's publication threshold: a county shows up by itself only at 50+ expected releases
TOLERANCE = 0.01   # sums of rounded figures may be off by up to 1% (or 2 children, whichever is larger)


def available(results=RESULTS) -> bool:
    return all((Path(results) / name).exists() for name in (MANIFEST, TABLE, CALIBRATION))


def load(results=RESULTS):
    results = Path(results)
    manifest = json.loads((results / MANIFEST).read_text(encoding="utf-8"))
    table = pd.read_csv(results / TABLE, dtype={"county_key": str, "county_fips": str})
    calibration = pd.read_csv(results / CALIBRATION)
    return manifest, table, calibration


def coverage(calibration: pd.DataFrame) -> dict:
    """Share of held-out actuals that fell inside their 80% range, pooled over years, per geo level."""
    pooled = calibration.groupby("geo_level")[["inside_80", "places"]].sum()
    return (pooled.inside_80 / pooled.places).round(3).to_dict()


def close(a, b) -> bool:
    return abs(a - b) <= max(TOLERANCE * abs(b), 2)


def problems(manifest: dict, table: pd.DataFrame, calibration: pd.DataFrame) -> list[str]:
    """Everything wrong with the scenario files, as plain sentences. An empty list means they pass."""
    found = []

    missing = [k for k in MANIFEST_KEYS if k not in manifest]
    if missing:
        return [f"scenarios.json is missing {', '.join(missing)}"]
    if [s.get("id") for s in manifest["scenarios"]] != list(SCENARIOS):
        found.append(f"scenarios.json must list the scenarios {', '.join(SCENARIOS)}, in that order")
    for s in manifest["scenarios"]:
        if not all(k in s for k in ("id", "label", "national_releases", "source_fiscal_year")):
            found.append(f"scenario {s.get('id')} needs id, label, national_releases and source_fiscal_year")
    if list(manifest["range"]) != [0.1, 0.9]:
        found.append("range must be [0.1, 0.9]: the 10th and 90th percentiles of the simulated draws")
    measures = {m.get("id"): m for m in manifest["measures"]}
    for m in REQUIRED_MEASURES:
        if m not in measures:
            found.append(f"scenarios.json has no '{m}' measure")
    for m in measures.values():
        if not (m.get("label") and m.get("definition")):
            found.append(f"measure {m.get('id')} needs a label and a plain-language definition")

    absent = [c for c in COLUMNS if c not in table.columns]
    if absent:
        return found + [f"scenario_releases.csv is missing columns {', '.join(absent)}"]
    if [c for c in CALIBRATION_COLUMNS if c not in calibration.columns]:
        found.append(f"scenario_calibration.csv needs columns {', '.join(CALIBRATION_COLUMNS)}")

    if not set(table.scenario) <= set(SCENARIOS):
        found.append("scenario_releases.csv has scenarios that are not in scenarios.json")
    if not set(table.geo_level) <= set(GEO_LEVELS):
        found.append(f"geo_level must be one of {', '.join(GEO_LEVELS)}")
    if not set(table.measure) <= set(measures):
        found.append("scenario_releases.csv has measures that scenarios.json does not define")

    nums = table[NUMBERS]
    if nums.isna().any().any():
        return found + ["expected, lower_80 and upper_80 must all be filled in"]
    if (nums % 1 != 0).any().any():
        found.append("figures must be rounded to whole children")
    if ((table.lower_80 < 0) | (table.lower_80 > table.expected) | (table.expected > table.upper_80)).any():
        found.append("every row needs 0 <= lower_80 <= expected <= upper_80")

    # Guardrail (NFR-03, FR-19): a county appears by itself only with 50+ expected releases. Below that
    # it belongs in the state's single "other counties" row.
    county = table[table.geo_level == "county"]
    if county.county_key.isna().any():
        found.append("every county row needs a county_key")
    small = county[(county.measure == "releases") & (county.expected < THRESHOLD)]
    if len(small):
        found.append(f"{len(small)} county rows show fewer than {THRESHOLD} expected releases by themselves; "
                     "fold them into their state's other counties row")
    with_releases = set(zip(county[county.measure == "releases"].scenario,
                            county[county.measure == "releases"].county_key))
    if not set(zip(county.scenario, county.county_key)) <= with_releases:
        found.append("a county appears for a service-need measure without a releases row")
    other = table[table.geo_level == "other_counties"]
    if other.county_key.notna().any():
        found.append("other counties rows must not carry a county_key")

    state = table[table.geo_level == "state"]
    keys = ["scenario", "state", "measure"]
    if set(state[keys].itertuples(index=False)) != set(other[keys].itertuples(index=False)):
        found.append("every state needs exactly one other counties row per scenario and measure")
    if other.duplicated(keys).any() or state.duplicated(keys).any():
        found.append("a state or other counties row is repeated")

    volumes = {s["id"]: s["national_releases"] for s in manifest["scenarios"]}
    for sid, total in state[state.measure == "releases"].groupby("scenario").expected.sum().items():
        if sid in volumes and not close(total, volumes[sid]):
            found.append(f"{sid}: state releases add up to {total:,.0f}, not the scenario's {volumes[sid]:,}")
    parts = table[table.geo_level != "state"].groupby(keys).expected.sum()
    whole = state.set_index(keys).expected
    off = [k for k in whole.index if not close(parts.get(k, 0), whole[k])]
    if off:
        found.append(f"{len(off)} state rows don't equal their counties plus other counties (first: {off[0]})")

    place = ["scenario", "geo_level", "state", "county_key"]
    if table.duplicated(place + ["measure"]).any():
        return found + ["a place appears more than once for the same scenario and measure"]
    wide = (table.assign(county_key=table.county_key.fillna(""))
            .set_index(place + ["measure"]).expected.unstack("measure"))
    if {"releases", "school_age"} <= set(wide.columns):
        if wide.school_age.isna().any():
            found.append("every place with releases needs a school_age row")
        if (wide.school_age > wide.releases).any():
            found.append("school-age children can't exceed children released for the same place")
    return found

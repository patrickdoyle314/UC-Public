"""Write a small, synthetic set of scenario files for the app tests.

The numbers are made up (round national totals, fixed shares) and are not estimates of anything.
They only follow the file format in docs/spec_week5_week6.md. Run: python tests/fixtures/make_scenario_fixture.py
"""
import json
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "scenarios"
VOLUMES = {"low": (20000, 2020), "median": (60000, 2016), "high": (120000, 2022)}
STATES = {"TX": ("Texas", 0.40), "CA": ("California", 0.35), "NY": ("New York", 0.25)}
COUNTIES = {  # share of the state's releases
    "TX": [("harris|TX", "48201", "Harris County, TX", 0.30), ("dallas|TX", "48113", "Dallas County, TX", 0.15)],
    "CA": [("los angeles|CA", "06037", "Los Angeles County, CA", 0.40)],
    "NY": [("queens|NY", "36081", "Queens County, NY", 0.20), ("suffolk|NY", "36103", "Suffolk County, NY", 0.15),
           ("westchester|NY", "36119", "Westchester County, NY", 0.008)],  # under 50 in the low scenario
}
SCHOOL_AGE = 0.5


def row(scenario, level, st, key, fips, name, measure, value):
    return dict(scenario=scenario, geo_level=level, state=st, state_name=STATES[st][0], county_key=key,
                county_fips=fips, county_name=name, measure=measure, expected=value,
                lower_80=round(value * 0.8), upper_80=round(value * 1.25))


def main():
    rows = []
    for scenario, (volume, _) in VOLUMES.items():
        for st, (_, share) in STATES.items():
            for measure, factor in (("releases", 1), ("school_age", SCHOOL_AGE)):
                total = round(volume * share * factor)
                rows.append(row(scenario, "state", st, None, None, None, measure, total))
                shown = 0
                for key, fips, name, cshare in COUNTIES[st]:
                    releases = round(volume * share * cshare)
                    if releases < 50:
                        continue  # folded into other counties, as the guardrail requires
                    value = round(releases * factor)
                    shown += value
                    rows.append(row(scenario, "county", st, key, fips, name, measure, value))
                rows.append(row(scenario, "other_counties", st, None, None, f"Other counties, {st}", measure,
                                total - shown))
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "scenario_releases.csv", index=False)

    calibration = [dict(fiscal_year=fy, geo_level=level, places=places, inside_80=round(places * 0.8),
                        coverage=round(round(places * 0.8) / places, 3))
                   for fy in range(2018, 2026) for level, places in (("state", 51), ("county", 120))]
    pd.DataFrame(calibration).to_csv(OUT / "scenario_calibration.csv", index=False)

    manifest = {
        "source": "test fixture",
        "base_fiscal_year": 2025,
        "share_model": "synthetic numbers for tests",
        "draws": 0,
        "seed": 0,
        "range": [0.1, 0.9],
        "scenarios": [{"id": s, "label": s.capitalize(), "national_releases": v, "source_fiscal_year": fy}
                      for s, (v, fy) in VOLUMES.items()],
        "measures": [
            {"id": "releases", "label": "Children released to sponsors",
             "definition": "Children expected to be released to sponsors in the place in one fiscal year."},
            {"id": "school_age", "label": "School-age children",
             "definition": "Synthetic: half of the children released."},
        ],
        "age_mix_source": "none (synthetic)",
    }
    (OUT / "scenarios.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

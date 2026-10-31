"""Scenario app: choose a national volume scenario and see expected releases and service needs by state and
county, with 80% ranges (Week 7, BRD FR-16 to FR-20).

Run from the repository root:   streamlit run app/streamlit_app.py

The scenario figures come from the Week 6 engine's files in results/ (format: docs/spec_week5_week6.md).
src/scenario_contract.py checks them first, and if anything fails, the app shows the problem instead of
the numbers. The History tab uses only published counts from the Week 1 table. UC_RESULTS_DIR points the
app at another folder of scenario files; the tests use it to load a synthetic fixture.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.terms import GLOSSARY, RANGE_PARTS  # noqa: E402
from src import scenario_contract as sc  # noqa: E402

RESULTS = Path(os.environ.get("UC_RESULTS_DIR", ROOT / "results"))
HISTORY = ROOT / "data/processed/releases_by_fy_geo.parquet"
COUNTY_SHAPES = ROOT / "data/raw/geo/cb_2023_us_county_20m.zip"
FISCAL_YEARS = list(range(2015, 2026))
ALL_STATES = "All states"
SCALE = px.colors.sequential.Blues[2:]  # skip the near-white steps so the smallest shaded place stays visible
UNSHADED = "#d9d9d6"
TICKS = [1, 10, 50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000]


@st.cache_data
def scenario_files(folder: str, stamp: float):  # stamp: newest file time, so edited files are re-read
    manifest, table, calibration = sc.load(folder)
    return manifest, table, calibration, sc.problems(manifest, table, calibration)


@st.cache_data
def history() -> pd.DataFrame:
    df = pd.read_parquet(HISTORY)
    return df[df.fiscal_year.isin(FISCAL_YEARS)]


@st.cache_data
def county_shapes(fips: tuple) -> dict:
    import geopandas as gpd  # only needed for the county maps
    shapes = gpd.read_file(f"zip://{COUNTY_SHAPES}")
    shapes = shapes[shapes.GEOID.isin(fips)].to_crs(4326)
    return json.loads(shapes[["GEOID", "NAME", "geometry"]].to_json())


def log_colorbar(values: pd.Series, title: str) -> dict:
    """Shading runs from tens to tens of thousands, so color follows log10 and the bar shows real counts."""
    lo, hi = max(values.min(), 1), max(values.max(), 1)
    ticks = [t for t in TICKS if lo / 2 <= t <= hi * 2] or [lo]
    return dict(title=title, tickvals=np.log10(ticks), ticktext=[f"{t:,}" for t in ticks])


def choropleth(rows: pd.DataFrame, value: str, title: str, hover: dict, counties: bool, zoom: bool):
    rows = rows.assign(shade=np.log10(rows[value].clip(lower=1)))
    common = dict(color="shade", color_continuous_scale=SCALE, hover_data=hover,
                  labels={k: v for k, v in GLOSSARY_LABELS.items() if k in rows})
    if counties:
        rows = rows.dropna(subset=["county_fips"])
        # The national view uses the Albers USA layout (Alaska and Hawaii inset); it can't zoom, so a single
        # state switches to a plain projection fitted to its counties.
        fig = px.choropleth(rows, geojson=county_shapes(tuple(sorted(rows.county_fips))), locations="county_fips",
                            featureidkey="properties.GEOID", hover_name="county_name",
                            **(common if zoom else dict(common, scope="usa")))
        fig.update_geos(showsubunits=True, subunitcolor="#9a9a96", showcountries=zoom)
        if zoom:
            fig.update_geos(fitbounds="locations", projection_type="mercator")
    else:
        fig = px.choropleth(rows, locations="state", locationmode="USA-states", hover_name="state_name", scope="usa",
                            **common)
    fig.update_geos(bgcolor="rgba(0,0,0,0)", showland=True, landcolor=UNSHADED, showlakes=False)
    fig.update_traces(marker_line_width=0.3, marker_line_color="white")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=360,
                      coloraxis_colorbar=log_colorbar(rows[value], title))
    return fig


GLOSSARY_LABELS = {"expected": "Expected", "lower_80": "Low end (80% range)", "upper_80": "High end (80% range)",
                   "releases": "Children released", "state": "State", "county_fips": "County FIPS"}


def wide_table(rows: pd.DataFrame, measures: list) -> pd.DataFrame:
    """One row per place; for each measure, expected value and both ends of the 80% range (FR-18)."""
    parts = []
    for m in measures:
        part = rows[rows.measure == m["id"]].set_index("place")[list(RANGE_PARTS)]
        part.columns = [f"{m['label']}: {RANGE_PARTS[c]}" for c in part.columns]
        parts.append(part)
    out = pd.concat(parts, axis=1).reset_index().rename(columns={"place": "Place"})
    return out.sort_values(out.columns[1], ascending=False)


def column_help(df: pd.DataFrame, measures: list) -> dict:
    definitions = {m["label"]: m["definition"] for m in measures}
    config = {}
    for col in df.columns:
        label, _, part = col.partition(": ")
        if part:
            text = f"{definitions.get(label, '')} {GLOSSARY[part.capitalize()]}"
            config[col] = st.column_config.NumberColumn(col, help=text, format="localized")
        else:
            config[col] = st.column_config.Column(col, help=GLOSSARY.get(col, ""))
    return config


# --------------------------------------------------------------------------- page

st.set_page_config(page_title="Unaccompanied children: planning scenarios", layout="wide")
st.title("Where unaccompanied children are placed: planning scenarios")
st.caption("For planning schools, legal aid and case management. Public, aggregate data only. Counties with fewer "
           "than 50 children released are never shown one by one; they are counted in their state's "
           "\"other counties\" figure.")

ready = False
if sc.available(RESULTS):
    stamp = max((RESULTS / f).stat().st_mtime for f in (sc.MANIFEST, sc.TABLE, sc.CALIBRATION))
    manifest, table, calibration, issues = scenario_files(str(RESULTS), stamp)
    if issues:
        st.error("The scenario files failed the app's checks, so none of their figures are shown:\n\n"
                 + "\n".join(f"- {p}" for p in issues))
    else:
        ready = True
        if manifest.get("source") == "test fixture":
            st.warning("Test data: these scenario figures are synthetic and describe nothing real.")
hist = history() if HISTORY.exists() else None

if ready:
    names = table.drop_duplicates("state").set_index("state").state_name.to_dict()
elif hist is not None:
    names = hist[hist.geo_level == "state"].drop_duplicates("state").set_index("state").state_name.to_dict()
else:
    names = {}

controls = st.columns([3, 2, 2])
if ready:
    scenarios = {s["id"]: s for s in manifest["scenarios"]}
    measures = manifest["measures"]
    by_id = {m["id"]: m for m in measures}
    scenario_id = controls[0].radio(
        "National volume scenario", list(scenarios), horizontal=True, help=GLOSSARY["Scenario"],
        format_func=lambda s: f"{scenarios[s]['label']}: {scenarios[s]['national_releases']:,} "
                              f"(FY{scenarios[s]['source_fiscal_year']} level)")
    measure_id = controls[1].selectbox("Map shows", list(by_id), format_func=lambda m: by_id[m]["label"])
state = controls[2].selectbox("State", [ALL_STATES] + sorted(names, key=names.get),
                              format_func=lambda s: names.get(s, s))
one_state = state != ALL_STATES

tab_scenario, tab_history, tab_terms, tab_about = st.tabs(["Scenario", "History", "Definitions",
                                                           "About and guardrails"])

with tab_scenario:
    if not ready:
        st.info("The scenario tables are not built yet. They come from the Week 6 scenario engine "
                "(src/scenarios.py), described in docs/spec_week5_week6.md. The History tab works now.")
    else:
        scen, m = scenarios[scenario_id], by_id[measure_id]
        rows = table[table.scenario == scenario_id].copy()
        rows["place"] = rows.county_name.where(rows.geo_level != "state", rows.state_name)
        states = rows[rows.geo_level == "state"]
        if one_state:
            rows = rows[rows.state == state]
        shown = rows[rows.measure == measure_id]

        left, right = st.columns(2)
        national = states[states.measure == measure_id].expected.sum()
        left.metric(f"{m['label']}, nationally", f"{national:,.0f}", help=m["definition"])
        if one_state:
            s_row = shown[shown.geo_level == "state"].iloc[0]
            right.metric(f"{m['label']}, {names[state]}", f"{s_row.expected:,.0f}",
                         help=f"80% range: {s_row.lower_80:,.0f} to {s_row.upper_80:,.0f}")
            right.caption(f"80% range: {s_row.lower_80:,.0f} to {s_row.upper_80:,.0f}")
        cover = sc.coverage(calibration)
        st.caption(f"{GLOSSARY['Expected']} {GLOSSARY['80% range']} In backtests of FY2018-FY2025, the ranges "
                   f"held the actual figure for {cover.get('state', 0):.0%} of states and "
                   f"{cover.get('county', 0):.0%} of listed counties. Share model: {manifest['share_model']}.")

        hover = {"shade": False, "expected": ":,", "lower_80": ":,", "upper_80": ":,", "state": False}
        map_l, map_r = st.columns(2)
        with map_l:
            st.markdown(f"**By state** ({m['label'].lower()}, expected)")
            st.plotly_chart(choropleth(shown[shown.geo_level == "state"], "expected", "Expected", hover,
                                       counties=False, zoom=False), key="scenario_states")
        with map_r:
            st.markdown(f"**Listed counties** ({m['label'].lower()}, expected)")
            if COUNTY_SHAPES.exists():
                st.plotly_chart(choropleth(shown[shown.geo_level == "county"], "expected", "Expected",
                                           dict(hover, county_fips=False), counties=True, zoom=one_state),
                                key="scenario_counties")
                st.caption("Grey: not shown one by one (in the state's other counties figure). Connecticut's "
                           "counties have no current Census shape and appear in the table only.")
            else:
                st.info("The county map needs the Census county boundary file in data/raw/geo (README > Data).")

        st.markdown("**States**" if not one_state else f"**{names[state]}**")
        state_table = wide_table(rows[rows.geo_level == "state"], measures)
        st.dataframe(state_table, hide_index=True, column_config=column_help(state_table, measures),
                     key="states_table")
        st.markdown("**Counties and other counties**")
        county_table = wide_table(rows[rows.geo_level != "state"], measures)
        st.dataframe(county_table, hide_index=True, column_config=column_help(county_table, measures),
                     key="counties_table")

with tab_history:
    if hist is None:
        st.info("History needs the Week 1 table: run python src/build_dataset.py, then python src/measure.py.")
    else:
        year = st.select_slider("Fiscal year", FISCAL_YEARS, value=FISCAL_YEARS[-1])
        st.caption("Published counts only. A county is shaded only in years with 50 or more children released.")
        this_year = hist[hist.fiscal_year == year]
        hover = {"shade": False, "releases": ":,", "state": False}
        map_l, map_r = st.columns(2)
        with map_l:
            st.markdown(f"**Children released to sponsors by state, FY{year}**")
            st.plotly_chart(choropleth(this_year[this_year.geo_level == "state"], "releases", "Children released",
                                       hover, counties=False, zoom=False), key="history_states")
        with map_r:
            st.markdown(f"**Listed counties, FY{year}**")
            listed = this_year[this_year.geo_level == "county"]
            if one_state:
                listed = listed[listed.state == state]
            if COUNTY_SHAPES.exists() and len(listed):
                st.plotly_chart(choropleth(listed, "releases", "Children released", dict(hover, county_fips=False),
                                           counties=True, zoom=one_state), key="history_counties")
            elif not len(listed):
                st.info(f"No county in {names.get(state, state)} had 50 or more children released in FY{year}.")

        level = hist[(hist.geo_level == "state") & (hist.state == state)] if one_state else \
            hist[hist.geo_level == "national"]
        where = names[state] if one_state else "United States"
        trend = px.line(level, x="fiscal_year", y="releases", markers=True,
                        labels={"fiscal_year": "Fiscal year", "releases": "Children released to sponsors"})
        trend.update_traces(line_width=2, marker_size=8)
        trend.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, yaxis_rangemode="tozero")
        st.markdown(f"**Children released to sponsors, {where}, FY2015-FY2025**")
        st.plotly_chart(trend, key="history_trend")

        counties = hist[hist.geo_level == "county"]
        if one_state:
            counties = counties[counties.state == state]
        steady = counties.groupby(["county_key", "county_name"]).agg(
            years=("fiscal_year", "nunique"), total=("releases", "sum")).reset_index()
        in_year = counties[counties.fiscal_year == year].set_index("county_key").releases
        steady["in_year"] = steady.county_key.map(in_year)
        steady = steady.sort_values(["years", "total"], ascending=False)
        if not one_state:
            steady = steady.head(25)
        steady = steady.rename(columns={"county_name": "County", "years": "Years listed (of 11)",
                                        "in_year": "Children released in selected year",
                                        "total": "Published total, FY2015-FY2025"})
        steady = steady[["County", "Years listed (of 11)", "Children released in selected year",
                         "Published total, FY2015-FY2025"]]
        st.markdown("**How steady is the need?** " + ("Listed counties" if one_state else
                                                      "The 25 most often listed counties"))
        st.dataframe(steady, hide_index=True, key="history_table", column_config={
            c: st.column_config.NumberColumn(c, help=GLOSSARY[c], format="localized") if c != "County"
            else st.column_config.Column(c, help=GLOSSARY[c]) for c in steady.columns})

with tab_terms:
    terms = dict(GLOSSARY)
    if ready:
        terms.update({m["label"]: m["definition"] for m in measures})
    st.dataframe(pd.DataFrame({"Term": list(terms), "Meaning": list(terms.values())}), hide_index=True,
                 key="terms_table")

with tab_about:
    st.markdown("""
**What this is for.** Schools, legal aid organizations and child welfare agencies plan staff and budgets months
ahead. This app shows where children released to sponsors have been placed, how steady that pattern is, and
what a low, median or high national year would mean for each state and listed county, with ranges.

**Guardrails**
1. Public, aggregate data only: the Migration Policy Institute's tabulation of ORR release data and Census
   population estimates.
2. Service planning only. Nothing here can be used to locate children, sponsors or households.
3. ORR's threshold is respected: counties with fewer than 50 children released are not shown one by one,
   and their counts are never estimated.
4. Neutral language; patterns are described, not blamed on anyone.
5. Figures are communities' service needs, not characteristics of the communities.

**Limits.** Counts are the first release location only; later moves are not tracked. Scenarios are planning
cases taken from FY2015-FY2025, not forecasts. Service-need figures use ORR's national age mix for children in
its care, which may differ from the children released to a given place.

**How this was built.** The app was written with AI assistance (Claude). The share model and the scenario
engine that produce the figures are the project owner's work; see the repository README.
""")

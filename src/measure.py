"""Week 3 measures with pandas and NumPy: how concentrated releases are, and how stable the pattern is.

Concentration, each fiscal year (BRD FR-07):
  HHI             sum of squared shares (1 = all in one place, 1/n = spread evenly over n)
  effective_n     1 / HHI, "as concentrated as this many equal-sized places"
  gini            inequality of shares, 0 (equal) to near 1 (all in one place)
  top10_share     share of releases in the 10 largest places
  Lorenz curves   results/lorenz_by_year.csv and results/figures/week3_lorenz.png
States: the 50 states and DC, computed exactly. Counties: shares of all releases that year. Counties
under 50 releases are not published and are never split or estimated, so county HHI is given as a
range (hhi_low to hhi), using only the fact that each unlisted county had at most 49 releases.

Persistence, each pair of consecutive fiscal years (FR-08): Spearman and Kendall rank correlation of
state shares, and of county counts among counties published in both years.

Tiers (plan Week 3): every county listed at least once is placed in a size tier each year (not listed,
50-199, 200-999, 1,000+ releases); a Markov transition matrix counts how often counties move between
tiers, pooled and for each pair of years. "Not listed" is ORR's published threshold, never an estimate.

Also writes data/processed/releases_by_fy_geo.parquet for DuckDB (sql/).

Usage: python src/measure.py   (after src/build_dataset.py)
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: Week 3 measures for service planning. How concentrated are releases (a few
# places or spread out)? Does the same set of states lead every year? Planners can then focus
# services (schools, legal aid, case management) where children consistently arrive.
#
# Python ideas: small pure functions on NumPy arrays (easy to test), pandas filtering and groupby,
# apply with a nested function, pivot (long table -> wide table), rank correlations, np.select and
# np.add.at for the tier transition counts.
# ===================================================================================================
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
FISCAL_YEARS = range(2015, 2026)
TERRITORIES = ("PR", "VI")  # left out so 'states' means the 50 states and DC


# --------------------------------------------------------------------------- metrics (pure NumPy)

# Each place's share of the total. np.asarray turns a list or a column into a NumPy array, so the math
# runs on all values at once. "-> np.ndarray" is a type hint: it documents what the function returns.
def shares(values) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    total = v.sum()
    return v / total if total > 0 else np.zeros_like(v)


# HHI is the standard concentration measure (antitrust regulators use it for market share). Two equal
# places give 0.5; ten equal places give 0.1.
def hhi(values) -> float:
    """Herfindahl-Hirschman index of the shares of `values`."""
    return float(np.sum(shares(values) ** 2))


# Sorted-values formula: G = 2 * sum(rank * value) / (n * total) - (n + 1) / n. It equals twice the area
# between the Lorenz curve and the line of perfect equality.
def gini(values) -> float:
    """Gini coefficient of non-negative `values` (0 = all equal)."""
    v = np.sort(np.asarray(values, dtype=float))
    n = v.size
    if n == 0 or v.sum() == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * v) / (n * v.sum())) - (n + 1) / n)


def top_share(values, n: int = 10) -> float:  # [::-1] reverses the sorted array (largest first); s[:n] keeps the first n
    s = np.sort(shares(values))[::-1]
    return float(s[:n].sum())


def lorenz(values) -> tuple[np.ndarray, np.ndarray]:  # for charts: the further the curve sags below the diagonal, the more concentrated
    """Lorenz curve points: cumulative share of places (x) vs cumulative share of releases (y)."""
    v = np.sort(np.asarray(values, dtype=float))
    x = np.arange(0, v.size + 1) / v.size
    y = np.concatenate([[0.0], np.cumsum(v) / v.sum()])
    return x, y


# --------------------------------------------------------------------------- data

# dtype={"county_fips": "string"} keeps FIPS codes as text so leading zeros survive (01001 is Autauga
# County, AL; read as a number it would become 1001).
def load() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "releases_by_fy_geo.csv", dtype={"county_fips": "string"})
    df["releases"] = df["releases"].astype("int64")
    return df


# Boolean filtering: each condition gives a True/False column; & means "and", ~ means "not". df[...]
# keeps the rows where every condition is True.
def state_table(df: pd.DataFrame) -> pd.DataFrame:
    s = df[(df.geo_level == "state") & ~df.state.isin(TERRITORIES) & df.fiscal_year.isin(FISCAL_YEARS)]
    return s[["fiscal_year", "state", "releases"]].reset_index(drop=True)


# The unlisted counties of every state are added into one national row per year (listed=False). It is
# used only as a total, never split into counties.
def county_table(df: pd.DataFrame) -> pd.DataFrame:
    """Listed counties (listed=True), plus all other counties nationally as one row per year."""
    c = df[df.fiscal_year.isin(FISCAL_YEARS)]
    listed = c[c.geo_level == "county"][["fiscal_year", "county_name", "releases"]].assign(listed=True)
    other = (c[c.geo_level == "other_counties"].groupby("fiscal_year", as_index=False)["releases"].sum()
             .assign(county_name="All other counties", listed=False))
    return pd.concat([listed, other], ignore_index=True)


# --------------------------------------------------------------------------- measures

# Shares are of all releases that year. For counties the unpublished ones are bounded, not estimated:
#   hhi_low = sum of squared listed shares (as if the unlisted counties added nothing)
#   hhi     = hhi_low + 49 * unlisted / total**2 (each unlisted county had at most 49 releases)
# so effective_n = 1 / hhi reads "at least this many equal-sized counties". Every listed county has 50+
# and every unlisted one under 50, so the top 10 are always listed and top10_share is exact. Gini is
# among the listed counties. States have nothing unlisted, so for them hhi_low = hhi exactly.
# groupby("fiscal_year").apply(per_year) runs per_year once per year and stacks the results into a
# table. per_year is defined inside concentration because nothing else uses it (a nested function).
def concentration(states: pd.DataFrame, counties: pd.DataFrame) -> pd.DataFrame:
    def per_year(g: pd.DataFrame, level: str) -> pd.Series:
        v = (g[g["listed"]] if "listed" in g else g)["releases"].to_numpy()
        total = g["releases"].sum()
        unlisted = total - v.sum()
        h_low = float(np.sum((v / total) ** 2))
        h = h_low + 49 * unlisted / total ** 2
        return pd.Series({"level": level, "places": len(v), "releases": int(total),
                          "hhi": round(h, 5), "hhi_low": round(h_low, 5),
                          "effective_n": round(1 / h, 1), "effective_n_high": round(1 / h_low, 1),
                          "gini": round(gini(v), 3), "top10_share": round(np.sort(v)[::-1][:10].sum() / total, 3),
                          "unlisted_share": round(unlisted / total, 3)})
    st = states.groupby("fiscal_year").apply(per_year, level="state", include_groups=False)
    co = counties.groupby("fiscal_year").apply(per_year, level="county", include_groups=False)
    return pd.concat([st, co]).reset_index().sort_values(["level", "fiscal_year"], ignore_index=True)


def lorenz_table(states: pd.DataFrame, counties: pd.DataFrame) -> pd.DataFrame:
    """Lorenz curve points for every year: states, and listed counties among themselves."""
    parts = []
    for level, t in (("state", states), ("county", counties[counties["listed"]])):
        for fy, g in t.groupby("fiscal_year"):
            x, y = lorenz(g["releases"])
            parts.append(pd.DataFrame({"fiscal_year": fy, "level": level, "place_share": x.round(4),
                                       "release_share": y.round(4)}))
    return pd.concat(parts, ignore_index=True)


def chart_lorenz(points: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    years = list(FISCAL_YEARS)
    cmap = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.35, 1, len(years))))  # light = FY2015, dark = FY2025
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, level, title in ((axes[0], "state", "States (50 + DC)"),
                             (axes[1], "county", "Listed counties (50+ releases), among themselves")):
        ax.plot([0, 1], [0, 1], color="#9a9a96", lw=1, ls="--")  # the diagonal: every place equal
        for i, fy in enumerate(years):
            p = points[(points.level == level) & (points.fiscal_year == fy)]
            ax.plot(p.place_share, p.release_share, color=cmap(i), lw=1.5)
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlabel("Share of places, smallest first")
        ax.spines[["top", "right"]].set_visible(False)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    axes[0].set_ylabel("Share of children released")
    norm = BoundaryNorm(np.arange(years[0] - 0.5, years[-1] + 1), cmap.N)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, ticks=[2015, 2020, 2025], label="Fiscal year")
    fig.savefig(FIG / "week3_lorenz.png", dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)


# Spearman and Kendall are rank correlations: 1 = the same order both years, 0 = unrelated. zip pairs
# each year with the next: (2015, 2016), (2016, 2017), ...
def pair_correlations(wide: pd.DataFrame, count_name: str) -> pd.DataFrame:
    rows = []
    for a, b in zip(wide.columns[:-1], wide.columns[1:]):
        pair = wide[[a, b]].dropna()
        rows.append({"from_fy": a, "to_fy": b, count_name: len(pair),
                     "spearman": round(pair[a].corr(pair[b], method="spearman"), 3),
                     "kendall": round(pair[a].corr(pair[b], method="kendall"), 3)})
    return pd.DataFrame(rows)


# Do the same states stay on top? .pivot turns the long table (one row per state-year) into a wide one
# (states x years); the trailing backslash continues the statement on the next line.
def persistence(states: pd.DataFrame) -> pd.DataFrame:
    wide = states.assign(share=states.groupby("fiscal_year")["releases"].transform(lambda r: r / r.sum())) \
                 .pivot(index="state", columns="fiscal_year", values="share")
    return pair_correlations(wide, "states")


# The same for counties published in both years. A county under 50 in either year has no count to rank,
# so it is left out of that pair; the tier transitions show counties crossing the threshold.
def county_persistence(df: pd.DataFrame) -> pd.DataFrame:
    c = df[(df.geo_level == "county") & df.fiscal_year.isin(FISCAL_YEARS)]
    wide = c.pivot_table(index="county_key", columns="fiscal_year", values="releases", aggfunc="sum")
    return pair_correlations(wide, "counties")


# Tiers: put every county-year into a size band, then count how often counties move between bands from
# one year to the next (a Markov transition matrix). Planners can read a row as "of the counties in this
# band this year, the share in each band next year". "Not listed" means under ORR's 50-release threshold
# that year: a published fact, so no unlisted county's count is ever estimated.
TIERS = ["not listed (<50)", "50-199", "200-999", "1,000+"]


def tier_codes(df: pd.DataFrame) -> pd.DataFrame:
    """One row per county listed at least once in FY2015-FY2025, one column per year: tier code 0-3."""
    c = df[(df.geo_level == "county") & df.fiscal_year.isin(FISCAL_YEARS)]
    wide = c.pivot_table(index="county_key", columns="fiscal_year", values="releases", aggfunc="sum")             .reindex(columns=list(FISCAL_YEARS))  # NaN = not listed that year
    # np.select takes the first condition that holds in each cell: 1,000+ -> 3, 200+ -> 2, listed -> 1, else 0
    codes = np.select([wide >= 1000, wide >= 200, wide.notna()], [3, 2, 1], default=0)
    return pd.DataFrame(codes, index=wide.index, columns=wide.columns)


def tier_transitions(codes: pd.DataFrame) -> pd.DataFrame:
    """Counts and row shares of year-to-year moves between tiers, pooled over all consecutive years."""
    a = codes.to_numpy()
    counts = np.zeros((len(TIERS), len(TIERS)), dtype=int)
    # Pair each year's tier (columns 0..n-2) with the next year's (1..n-1); np.add.at adds 1 per pair.
    np.add.at(counts, (a[:, :-1].ravel(), a[:, 1:].ravel()), 1)
    totals = counts.sum(axis=1, keepdims=True)
    probs = np.divide(counts, totals, out=np.zeros(counts.shape), where=totals > 0)  # row shares; 0 if a row is empty
    return pd.DataFrame([{"from_tier": TIERS[i], "to_tier": TIERS[j], "county_years": int(counts[i, j]),
                          "probability": round(float(probs[i, j]), 3)}
                         for i in range(len(TIERS)) for j in range(len(TIERS))])


def tier_transitions_by_year(codes: pd.DataFrame) -> pd.DataFrame:
    """The same matrix for each pair of consecutive years (BRD FR-08)."""
    parts = [tier_transitions(codes[[a, b]]).assign(from_fy=a, to_fy=b)
             for a, b in zip(codes.columns[:-1], codes.columns[1:])]
    out = pd.concat(parts, ignore_index=True).rename(columns={"county_years": "counties"})
    return out[["from_fy", "to_fy", "from_tier", "to_tier", "counties", "probability"]]


def tiers_by_year(codes: pd.DataFrame) -> pd.DataFrame:
    """How many of the ever-listed counties sit in each tier, per fiscal year."""
    # np.bincount counts how many times each code 0..3 appears in a year's column
    out = pd.DataFrame({fy: np.bincount(codes[fy], minlength=len(TIERS)) for fy in codes.columns}, index=TIERS).T
    return out.rename_axis("fiscal_year").reset_index()


def main():  # write the parquet copy for SQL, compute the tables, save them to results/
    df = load()
    df.to_parquet(PROCESSED / "releases_by_fy_geo.parquet", index=False)  # parquet: a compact, typed file format that DuckDB reads very fast
    states, counties = state_table(df), county_table(df)
    conc, pers = concentration(states, counties), persistence(states)
    FIG.mkdir(parents=True, exist_ok=True)
    conc.to_csv(RESULTS / "concentration_by_year.csv", index=False)
    pers.to_csv(RESULTS / "persistence_state_ranks.csv", index=False)
    county_pers = county_persistence(df)
    county_pers.to_csv(RESULTS / "persistence_county_ranks.csv", index=False)
    points = lorenz_table(states, counties)
    points.to_csv(RESULTS / "lorenz_by_year.csv", index=False)
    chart_lorenz(points)
    codes = tier_codes(df)
    trans = tier_transitions(codes)
    trans.to_csv(RESULTS / "tier_transitions.csv", index=False)
    tier_transitions_by_year(codes).to_csv(RESULTS / "tier_transitions_by_year.csv", index=False)
    tiers_by_year(codes).to_csv(RESULTS / "county_tiers_by_year.csv", index=False)
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(conc.to_string(index=False))
        print()
        print(pers.merge(county_pers, on=["from_fy", "to_fy"], suffixes=("_states", "_counties")).to_string(index=False))
        print()
        print(trans.pivot(index="from_tier", columns="to_tier", values="probability").reindex(TIERS)[TIERS])


if __name__ == "__main__":
    main()

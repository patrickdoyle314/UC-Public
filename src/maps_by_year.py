"""State and county maps of children released to sponsors for every fiscal year, FY2015-FY2025 (BRD FR-06).

Week 2 mapped the eleven-year totals. These small multiples show each year on one shared color scale, so a
planner can see the FY2021-FY2024 rise and the FY2025 fall place by place. County panels shade only
published counts (50+ releases); every other county stays grey and nothing is estimated for it.

Run after src/measure.py:   python src/maps_by_year.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.geography import FIG, FISCAL_YEARS, MUTED, load, shapes  # noqa: E402

GREY = "#e4e4e1"
# Blues without its near-white end, so the smallest shaded place is still visible against the grey
BLUES = LinearSegmentedColormap.from_list("blues", plt.get_cmap("Blues")(range(70, 256)))
NOTE = ("Contiguous U.S.; Alaska, Hawaii, Puerto Rico and the Virgin Islands are not drawn. Connecticut's listed "
        "counties have no current Census shape.")


def panels(title: str):
    fig, axes = plt.subplots(3, 4, figsize=(13, 7.6))
    for ax in axes.flat:
        ax.set_axis_off()
    fig.suptitle(title, x=0.01, ha="left", fontsize=11)
    fig.text(0.01, 0.01, NOTE, fontsize=7, color=MUTED)
    return fig, axes.flat


def colorbar(fig, norm, label: str):
    cax = fig.add_axes([0.80, 0.16, 0.012, 0.18])  # sits in the empty twelfth panel
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=BLUES), cax=cax)
    bar.set_label(label, fontsize=8)
    bar.ax.tick_params(labelsize=7)
    bar.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))


def state_maps(df, st):
    rel = df[df.geo_level == "state"].pivot(index="state", columns="fiscal_year", values="releases")
    norm = LogNorm(vmin=10, vmax=rel[FISCAL_YEARS].max().max())
    fig, axes = panels("Children released to sponsors by state, each fiscal year (shared log scale)")
    for ax, fy in zip(axes, FISCAL_YEARS):
        g = st.assign(releases=st.STUSPS.map(rel[fy]))
        g.plot(color=GREY, linewidth=0.3, edgecolor="white", ax=ax)
        shaded = g[g.releases > 0]
        shaded.plot(column=shaded.releases.clip(lower=10), cmap=BLUES, norm=norm, linewidth=0.3,
                    edgecolor="white", ax=ax)
        ax.set_title(f"FY{fy}: {int(rel[fy].sum()):,}", fontsize=9, loc="left")
    colorbar(fig, norm, "Children released\n(grey: none; under 10 drawn as 10)")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.04, wspace=0.02, hspace=0.12)
    fig.savefig(FIG / "week7_state_maps_by_year.png", dpi=200, facecolor="white")
    plt.close(fig)


def county_maps(df, st, co):
    drawable = df[(df.geo_level == "county") & df.county_fips.notna()]  # Connecticut's 4 have no FIPS match
    rel = drawable.pivot(index="county_fips", columns="fiscal_year", values="releases")
    norm = LogNorm(vmin=50, vmax=rel[FISCAL_YEARS].max().max())
    fig, axes = panels("Listed counties (50+ children released to sponsors), each fiscal year (shared log scale)")
    for ax, fy in zip(axes, FISCAL_YEARS):
        g = co.assign(releases=co.GEOID.map(rel[fy]))
        g.plot(color=GREY, linewidth=0, ax=ax)
        listed = g[g.releases.notna()]
        listed.plot(column="releases", cmap=BLUES, norm=norm, linewidth=0, ax=ax)
        st.boundary.plot(ax=ax, color="#9a9a96", linewidth=0.2)
        ax.set_title(f"FY{fy}: {len(listed)} counties shown", fontsize=9, loc="left")
    colorbar(fig, norm, "Children released\n(grey: under 50, not published)")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.04, wspace=0.02, hspace=0.12)
    fig.savefig(FIG / "week7_county_maps_by_year.png", dpi=200, facecolor="white")
    plt.close(fig)


def main():
    df = load()
    df = df[df.fiscal_year.isin(FISCAL_YEARS)]
    st, co = shapes()
    state_maps(df, st)
    county_maps(df, st, co)
    print("wrote results/figures/week7_state_maps_by_year.png and week7_county_maps_by_year.png")


if __name__ == "__main__":
    main()

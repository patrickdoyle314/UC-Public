"""Week 2 acceptance checks on the saved notebook (BRD FR-05, FR-06 and the Week 2 review question).

They read notebooks/week2_eda.ipynb as committed, so rebuild it with
    python notebooks/build_week2_eda.py
after changing the builder or the Week 1 table.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "notebooks" / "build_week2_eda.py"
CELLS = json.loads((ROOT / "notebooks" / "week2_eda.ipynb").read_text(encoding="utf-8"))["cells"]


def text(cell):
    src = cell["source"]
    return src if isinstance(src, str) else "".join(src)


def images(cell):
    return sum("image/png" in o.get("data", {}) for o in cell.get("outputs", []))


def printed(cell):
    return "".join("".join(o["text"]) if isinstance(o.get("text"), list) else o.get("text", "")
                   for o in cell.get("outputs", []))


def code_after(heading):
    i = next(i for i, c in enumerate(CELLS) if c["cell_type"] == "markdown" and text(c).startswith(heading))
    return next(c for c in CELLS[i + 1:] if c["cell_type"] == "code")


def test_five_findings_each_backed_by_a_chart():  # FR-05
    headings = [text(c) for c in CELLS if c["cell_type"] == "markdown" and re.match(r"## \d\. ", text(c))]
    assert [h[3] for h in headings] == list("12345")
    assert all(images(code_after(h[:5])) >= 1 for h in headings)


def test_state_and_county_maps_for_every_year():  # FR-06
    cell = code_after("### The same maps for every fiscal year")
    assert images(cell) == 2
    assert "for ax, fy in zip(axes, FY)" in text(cell)
    for name in ("state", "county"):
        assert (ROOT / "results" / "figures" / f"week2_{name}_maps_by_year.png").exists()


def test_week1_table_reconciles_before_any_finding():  # Week 2 review question
    out = printed(code_after("## Before the findings"))
    checked = re.search(r"(\d+) of (\d+) state-years", out)
    assert checked and checked.group(1) == checked.group(2) == str(53 * 11)
    assert "all 11 years" in out


def test_reads_nothing_from_later_weeks():
    source = BUILDER.read_text(encoding="utf-8")
    reads = re.findall(r"read_\w+\(([^\n]*)", source)
    # every file read is Week 1's table or a raw boundary file, never a Week 3+ output
    assert reads and all("data/processed/releases_by_fy_geo.csv" in r or "geo /" in r for r in reads)

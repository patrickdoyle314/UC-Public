"""Plain-language definitions for every term the app shows (BRD FR-20). Column help text comes from here."""

GLOSSARY = {
    "Unaccompanied children": "Children who arrive in the United States without a parent or legal guardian and are "
                              "placed in the care of the Office of Refugee Resettlement (ORR).",
    "Released to sponsors": "ORR discharges a child from its care to a sponsor, usually a parent, relative or family "
                            "friend, who lives in a U.S. community. Counts are by the sponsor's county at the time of "
                            "release; later moves are not tracked.",
    "Fiscal year": "The federal fiscal year, October 1 to September 30. FY2025 ran from October 2024 through "
                   "September 2025.",
    "Scenario": "A possible national total of children released in one year, taken from the record: the lowest "
                "(Low), middle (Median) and highest (High) years from FY2015 to FY2025. It is a planning case, "
                "not a forecast.",
    "Place": "A state, a listed county, or a state's other counties.",
    "Expected": "The average over all simulated outcomes for the scenario.",
    "Low end": "The lower end of the 80% range: in 1 of 10 simulated outcomes the figure is below it.",
    "High end": "The upper end of the 80% range: in 1 of 10 simulated outcomes the figure is above it.",
    "80% range": "In 8 of 10 simulated outcomes the figure falls between the low end and the high end.",
    "Listed county": "A county with 50 or more children released in a fiscal year. Only these counties are "
                     "published by name.",
    "Other counties": "All of a state's counties below the 50-release threshold, as one figure. The app never "
                      "splits it up or shows those counties one by one.",
    "County": "A listed county, named as in the published data.",
    "Years listed (of 11)": "How many of the 11 fiscal years FY2015-FY2025 the county had 50 or more children "
                            "released. A high number means steady need; a low number means need that comes and goes.",
    "Children released in selected year": "The published count for the fiscal year chosen above. Blank means the "
                                          "county had fewer than 50 that year, so it is part of other counties.",
    "Published total, FY2015-FY2025": "The sum of the county's published counts. Years under 50 are not "
                                      "published, so they are not included.",
    "Share": "A state's or county's part of the national (or state) total in a year.",
}

# Range columns in the scenario tables are named "<measure label>: <part>"
RANGE_PARTS = {"expected": "expected", "lower_80": "low end", "upper_80": "high end"}

#!/usr/bin/env python3
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Compute effective faculties, publication counts, effort per paper, and ICLR point by research area."
    )
    parser.add_argument(
        "--start_year",
        type=int,
        default=2019,
        help="Start year (inclusive). Default: 2019",
    )
    parser.add_argument(
        "--end_year", type=int, default=2023, help="End year (inclusive). Default: 2023"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="iclr.csv",
        help="Output CSV file name. Default: iclr.csv",
    )
    args = parser.parse_args()

    start_year = args.start_year
    end_year = args.end_year

    # Load CSV files.
    authors = pd.read_csv("generated-author-info.csv")
    pubs = pd.read_csv("area_publications.csv")
    confs = pd.read_csv("conferences.csv")

    # Filter out conferences where NextTier is true.
    # (We convert NextTier to string and compare lowercased to "false".)
    confs = confs[confs["NextTier"].astype(str).str.lower() == "false"]

    # Build mapping from conference code to its research area.
    # In conferences.csv, the column "Conference" is the code used in the other files,
    # and the column "Area" holds the research group (e.g. mlmining, ai, vision, etc.).
    conf_to_area = confs.set_index("Conference")["Area"].to_dict()

    #########################
    # (1) Effective Faculties
    #########################
    # Filter the generated-author-info.csv for years and valid conferences.
    authors_filtered = authors[
        (authors["year"] >= start_year) & (authors["year"] <= end_year)
    ]
    authors_filtered = authors_filtered[
        authors_filtered["area"].isin(conf_to_area.keys())
    ].copy()
    # Map the conference code to research area.
    authors_filtered["research_area"] = authors_filtered["area"].map(conf_to_area)

    # For each faculty, get the set of research areas they published in.
    faculty_groups = authors_filtered.groupby("name")["research_area"].unique()

    # Each faculty contributes 1/number_of_areas in each research area they published.
    effective_faculties = {}
    for faculty, areas in faculty_groups.items():
        weight = 1 / len(areas)
        for area in areas:
            effective_faculties[area] = effective_faculties.get(area, 0) + weight

    #########################
    # (2) Publication Count
    #########################
    # Filter area_publications.csv for the period and valid conferences.
    pubs_filtered = pubs[(pubs["Year"] >= start_year) & (pubs["Year"] <= end_year)]
    pubs_filtered = pubs_filtered[
        pubs_filtered["Area"].isin(conf_to_area.keys())
    ].copy()
    # Map each row's conference code to research area.
    pubs_filtered["research_area"] = pubs_filtered["Area"].map(conf_to_area)
    # Sum publication counts per research area.
    pub_counts = (
        pubs_filtered.groupby("research_area")["PublicationCount"].sum().to_dict()
    )

    #########################
    # (3) Effort per Paper
    #########################
    # For each research area, compute effective_faculties / publication count.
    all_areas = set(effective_faculties.keys()) | set(pub_counts.keys())
    results = []
    for area in all_areas:
        fac_count = effective_faculties.get(area, 0)
        pub_count = pub_counts.get(area, 0)
        effort = fac_count / pub_count if pub_count > 0 else 0
        results.append(
            {
                "Area": area,
                "EffectiveFaculties": fac_count,
                "PublicationCount": pub_count,
                "EffortPerPaper": effort,
            }
        )

    results_df = pd.DataFrame(results)

    #########################
    # (4) ICLR Point Computation
    #########################
    # Use mlmining as the baseline. Find the effort for mlmining.
    baseline_row = results_df[results_df["Area"] == "mlmining"]
    if not baseline_row.empty:
        baseline_effort = baseline_row.iloc[0]["EffortPerPaper"]
    else:
        baseline_effort = None

    if baseline_effort and baseline_effort != 0:
        results_df["ICLRPoint"] = results_df["EffortPerPaper"] / baseline_effort
    else:
        results_df["ICLRPoint"] = None

    # Output the result to a CSV file.
    results_df.to_csv(args.output, index=False)
    print(f"Output written to {args.output}")


if __name__ == "__main__":
    main()

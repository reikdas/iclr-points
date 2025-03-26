#!/usr/bin/env python3
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Compute Adjusted ICLR points for institutes based on generated-author-info.csv, iclr.csv, and conferences.csv."
    )
    parser.add_argument(
        "--start_year",
        type=int,
        default=2019,
        help="Start year (inclusive) for filtering publications. Default: 2019",
    )
    parser.add_argument(
        "--end_year",
        type=int,
        default=2023,
        help="End year (inclusive) for filtering publications. Default: 2023",
    )
    parser.add_argument(
        "--ranked_output",
        type=str,
        default="institute_adjusted_ranked.csv",
        help="Output CSV file for ranked institutes (overall adjusted points).",
    )
    parser.add_argument(
        "--detailed_output",
        type=str,
        default="institute_adjusted_details.csv",
        help="Output CSV file for detailed breakdown (institute, area, adjusted points).",
    )
    args = parser.parse_args()

    # Load conferences.csv to map conference codes (the 'area' field in author data)
    # to the real research areas.
    confs = pd.read_csv("conferences.csv")
    # Filter out conferences marked as NextTier.
    confs = confs[confs["NextTier"].astype(str).str.lower() == "false"]
    conf_to_area = confs.set_index("Conference")["Area"].to_dict()

    # Load iclr.csv to get ICLR points per research area.
    iclr_df = pd.read_csv("iclr.csv")
    area_to_iclr = iclr_df.set_index("Area")["ICLRPoint"].to_dict()

    # Load generated-author-info.csv and filter by the specified year range.
    auth_df = pd.read_csv("generated-author-info.csv")
    auth_df = auth_df[
        (auth_df["year"] >= args.start_year) & (auth_df["year"] <= args.end_year)
    ]

    # Map each publication row to its real research area using the conference mapping.
    auth_df["real_area"] = auth_df["area"].map(conf_to_area)

    # Map ICLR point to each row based on its real area.
    auth_df["ICLRPoint"] = auth_df["real_area"].map(area_to_iclr)
    auth_df["ICLRPoint"] = auth_df["ICLRPoint"].fillna(0)

    # Compute the adjusted ICLR points for each publication row.
    auth_df["RowAdjICLRPoints"] = auth_df["adjustedcount"] * auth_df["ICLRPoint"]

    # Compute overall adjusted ICLR points for each institute.
    # We assume the "dept" field corresponds to the institute.
    institute_points = auth_df.groupby("dept")["RowAdjICLRPoints"].sum().reset_index()
    institute_points = institute_points.rename(
        columns={"dept": "Institute", "RowAdjICLRPoints": "AdjustedICLRPoints"}
    )
    ranked_df = institute_points.sort_values(by="AdjustedICLRPoints", ascending=False)

    ranked_df.to_csv(args.ranked_output, index=False)
    print(f"Ranked institute adjusted ICLR points written to {args.ranked_output}")

    # Compute detailed breakdown: for each institute and research area,
    # sum the adjusted ICLR points.
    detailed_df = (
        auth_df.groupby(["dept", "real_area"])["RowAdjICLRPoints"].sum().reset_index()
    )
    detailed_df = detailed_df.rename(
        columns={
            "dept": "Institute",
            "real_area": "Area",
            "RowAdjICLRPoints": "AdjustedICLRPoints",
        }
    )
    # Sort the detailed output by institute (alphabetically) then by area.
    detailed_df = detailed_df.sort_values(by=["Institute", "Area"])

    detailed_df.to_csv(args.detailed_output, index=False)
    print(f"Detailed institute breakdown written to {args.detailed_output}")


if __name__ == "__main__":
    main()

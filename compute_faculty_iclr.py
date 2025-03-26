#!/usr/bin/env python3
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser(
        description="Compute ICLR points per faculty based on iclr.csv, generated-author-info.csv, and conferences.csv."
    )
    parser.add_argument("--current_year", type=int, default=2024,
                        help="Current year to compute per-year metrics (default: 2024)")
    parser.add_argument("--detailed_output", type=str, default="faculty_iclr_details.csv",
                        help="Output CSV file name for detailed faculty metrics (default: faculty_iclr_details.csv)")
    parser.add_argument("--top10_output", type=str, default="faculty_iclr_top10.csv",
                        help="Output CSV file name for top 10 rankings (default: faculty_iclr_top10.csv)")
    args = parser.parse_args()
    
    # Load conferences.csv to map conference code to its actual research area.
    confs = pd.read_csv("conferences.csv")
    # Filter out NextTier conferences.
    confs = confs[confs["NextTier"].astype(str).str.lower() == "false"]
    # Build mapping: conference code -> research area
    conf_to_area = confs.set_index("Conference")["Area"].to_dict()
    
    # Load the ICLR points per research area (from iclr.csv).
    iclr_df = pd.read_csv("iclr.csv")
    # Build mapping: real research area -> ICLRPoint
    area_to_iclr = iclr_df.set_index("Area")["ICLRPoint"].to_dict()
    
    # Load the faculty publication data.
    auth_df = pd.read_csv("generated-author-info.csv")
    
    # Map each publication row to its actual research area using the conferences mapping.
    auth_df["real_area"] = auth_df["area"].map(conf_to_area)
    
    # Map ICLR point to each publication row based on its real area.
    auth_df["ICLRPoint"] = auth_df["real_area"].map(area_to_iclr)
    auth_df["ICLRPoint"] = auth_df["ICLRPoint"].fillna(0)
    
    # Compute the ICLR contribution for each publication.
    auth_df["RowICLRPoints"] = auth_df["count"] * auth_df["ICLRPoint"]
    auth_df["RowAdjICLRPoints"] = auth_df["adjustedcount"] * auth_df["ICLRPoint"]
    
    # Group by faculty ("name") and aggregate metrics.
    group = auth_df.groupby("name")
    faculty_stats = group.agg(
        TotalICLRPoints=("RowICLRPoints", "sum"),
        AdjICLRPoints=("RowAdjICLRPoints", "sum"),
        StartYear=("year", "min"),
        Dept=("dept", "first"),
        NumAreas=("real_area", "nunique")
    ).reset_index()
    
    # Compute years active using the provided current year.
    faculty_stats["YearsActive"] = args.current_year - faculty_stats["StartYear"] + 1
    faculty_stats["TotalICLRPointsPerYear"] = faculty_stats["TotalICLRPoints"] / faculty_stats["YearsActive"]
    faculty_stats["AdjICLRPointsPerYear"] = faculty_stats["AdjICLRPoints"] / faculty_stats["YearsActive"]
    
    # Arrange columns (adding NumAreas as the last column).
    faculty_stats = faculty_stats[["name", "Dept", "StartYear", "YearsActive",
                                     "TotalICLRPoints", "AdjICLRPoints",
                                     "TotalICLRPointsPerYear", "AdjICLRPointsPerYear",
                                     "NumAreas"]]
    
    # Write the detailed output.
    faculty_stats.to_csv(args.detailed_output, index=False)
    print(f"Detailed faculty metrics written to {args.detailed_output}")
    
    # Build the top-10 rankings for each metric.
    top10_dfs = []
    metrics = [
        ("TotalICLRPoints", "Total ICLR Points"),
        ("AdjICLRPoints", "Adjusted ICLR Points"),
        ("TotalICLRPointsPerYear", "Total ICLR Points Per Year"),
        ("AdjICLRPointsPerYear", "Adjusted ICLR Points Per Year")
    ]
    
    for col, metric_name in metrics:
        top10 = faculty_stats.sort_values(by=col, ascending=False).head(10).copy()
        top10["Metric"] = metric_name
        # Reorder so that the "Metric" column comes first.
        cols = ["Metric"] + list(top10.columns.drop("Metric"))
        top10 = top10[cols]
        top10_dfs.append(top10)
    
    top10_all = pd.concat(top10_dfs, ignore_index=True)
    top10_all.to_csv(args.top10_output, index=False)
    print(f"Top 10 rankings for each metric written to {args.top10_output}")

if __name__ == "__main__":
    main()
import argparse
import csv
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(
        description="Compute publications per faculty and ICLR Points by parent area using faculty and publication data."
    )
    parser.add_argument(
        "--faculty",
        type=str,
        default="faculty_parent_area_counts.csv",
        help="CSV file with faculty counts (default: faculty_parent_area_counts.csv)"
    )
    parser.add_argument(
        "--publications",
        type=str,
        default="parent_area_publications.csv",
        help="CSV file with publication counts per parent area per year (default: parent_area_publications.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="pubs_per_faculty_with_iclr.csv",
        help="Output CSV file (default: pubs_per_faculty_with_iclr.csv)"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2019,
        help="Start year for publication aggregation (default: 2019)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2023,
        help="End year for publication aggregation (default: 2023)"
    )
    args = parser.parse_args()

    # Read faculty counts: mapping ParentArea -> FacultyCount
    faculty_counts = {}
    with open(args.faculty, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            area = row["ParentArea"].strip().lower()
            try:
                count = float(row["FacultyCount"])
            except ValueError:
                continue
            faculty_counts[area] = count

    # Aggregate publication counts for the specified year range.
    pub_counts = defaultdict(int)
    with open(args.publications, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            area = row["ParentArea"].strip().lower()
            try:
                year = int(row["Year"])
            except ValueError:
                continue
            if args.start_year <= year <= args.end_year:
                try:
                    count = int(row["PublicationCount"])
                except ValueError:
                    continue
                pub_counts[area] += count

    # Compute publications per faculty for each area (ratio = pub_count / faculty_count)
    pubs_per_faculty = {}
    results = []
    for area, pub_count in pub_counts.items():
        fac_count = faculty_counts.get(area, 0.0)
        ratio = pub_count / fac_count if fac_count > 0 else 0.0
        pubs_per_faculty[area] = ratio
        results.append((area, fac_count, pub_count, ratio))

    # Determine the mlmining publications per faculty ratio.
    mlmining_ratio = pubs_per_faculty.get("mlmining", 0.0)

    # Compute NeruIPS Points: mlmining_ratio / (area ratio), with 0 if area ratio is 0.
    final_results = []
    for area, fac_count, pub_count, ratio in results:
        neruips_points = (mlmining_ratio / ratio) if ratio != 0 else 0.0
        final_results.append((area, fac_count, pub_count, ratio, neruips_points))

    # Write the output CSV with an additional column "NeruIPS Points"
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ParentArea", "FacultyCount", "PublicationCount", "PublicationsPerFaculty", "ICLR Points"])
        # Sort results by parent area name
        for row in sorted(final_results):
            writer.writerow(row)

    print("Publications per faculty with ICLR Points computed and written to", args.output)

if __name__ == '__main__':
    main()
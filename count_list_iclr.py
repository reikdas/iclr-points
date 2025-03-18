#!/usr/bin/env python3
"""
Compute total ICLR points per author from a publication report and include the candidate’s dominant parentparentarea.

Usage:
    python iclr_points_computation.py --report publication_report.csv --names input_names.csv [--pubs-file pubs_per_faculty_with_iclr.csv] [--include-next-tier]

The script reads:
  - A publication report CSV file (with columns: name,area,year,first_author_count,all_publication_count,weighted_publication_count)
  - A names CSV file (with a "name" column). All names from this file will be included in the final output.
  - A CSV file with ICLR points per parent area (default: pubs_per_faculty_with_iclr.csv).

For each row in the publication report, the script:
  1. Maps the paper’s area to its parent area (using parent_map) and then to its parentparentarea (via parent_parent_map).
  2. Increments a count for that candidate and parentparentarea.
  3. Computes ICLR points for that paper (using special handling for theory areas).
Totals per author are aggregated and, in the output CSV, a new column “parent_parent_area” shows the single parentparentarea in which
the candidate has the most papers (if available). Papers from nextTier areas are ignored unless the --include-next-tier flag is provided.
"""

import argparse
import csv
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Compute total ICLR points per author with dominant parentparentarea."
    )
    parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="CSV file containing the publication report.",
    )
    parser.add_argument(
        "--names",
        type=str,
        required=True,
        help="CSV file containing the list of names (with a column 'name'). All names from this file will be included in the output.",
    )
    parser.add_argument(
        "--pubs-file",
        type=str,
        default="pubs_per_faculty_with_iclr.csv",
        help="CSV file with ICLR points (default: pubs_per_faculty_with_iclr.csv).",
    )
    parser.add_argument(
        "--include-next-tier",
        action="store_true",
        help="Include nextTier areas in the computation (by default they are ignored).",
    )
    args = parser.parse_args()

    # Mapping from area (lowercase) to parent area.
    parent_map = {
        'aaai': 'ai',
        'ijcai': 'ai',
        'cvpr': 'vision',
        'eccv': 'vision',
        'iccv': 'vision',
        'icml': 'mlmining',
        'iclr': 'mlmining',
        'kdd': 'mlmining',
        'nips': 'mlmining',
        'acl': 'nlp',
        'emnlp': 'nlp',
        'naacl': 'nlp',
        'sigir': 'inforet',
        'www': 'inforet',
        'asplos': 'arch',
        'isca': 'arch',
        'micro': 'arch',
        'hpca': 'arch',
        'ccs': 'sec',
        'oakland': 'sec',
        'usenixsec': 'sec',
        'ndss': 'sec',
        'pets': 'sec',
        'vldb': 'mod',
        'sigmod': 'mod',
        'icde': 'mod',
        'pods': 'mod',
        'dac': 'da',
        'iccad': 'da',
        'emsoft': 'bed',
        'rtas': 'bed',
        'rtss': 'bed',
        'sc': 'hpc',
        'hpdc': 'hpc',
        'ics': 'hpc',
        'mobicom': 'mobile',
        'mobisys': 'mobile',
        'sensys': 'mobile',
        'imc': 'metrics',
        'sigmetrics': 'metrics',
        'osdi': 'ops',
        'sosp': 'ops',
        'eurosys': 'ops',
        'fast': 'ops',
        'usenixatc': 'ops',
        'popl': 'plan',
        'pldi': 'plan',
        'oopsla': 'plan',
        'icfp': 'plan',
        'fse': 'soft',
        'icse': 'soft',
        'ase': 'soft',
        'issta': 'soft',
        'nsdi': 'comm',
        'sigcomm': 'comm',
        'siggraph': 'graph',
        'siggraph-asia': 'graph',
        'eurographics': 'graph',
        'focs': 'act',
        'soda': 'act',
        'stoc': 'act',
        'crypto': 'crypt',
        'eurocrypt': 'crypt',
        'cav': 'log',
        'lics': 'log',
        'ismb': 'bio',
        'recomb': 'bio',
        'ec': 'ecom',
        'wine': 'ecom',
        'chiconf': 'chi',
        'ubicomp': 'chi',
        'uist': 'chi',
        'icra': 'robotics',
        'iros': 'robotics',
        'rss': 'robotics',
        'vis': 'visualization',
        'vr': 'visualization',
        'sigcse': 'csed'
    }

    # Mapping from parent area to parentparentarea.
    parent_parent_map = {
        "ai": "AI",
        "vision": "AI",
        "mlmining": "AI",
        "nlp": "AI",
        "inforet": "AI",
        "arch": "Systems",
        "comm": "Systems",
        "sec": "Systems",
        "mod": "Systems",
        "da": "Systems",
        "bed": "Systems",
        "hpc": "Systems",
        "mobile": "Systems",
        "metrics": "Systems",
        "ops": "Systems",
        "plan": "Systems",
        "soft": "Systems",
        "act": "Theory",
        "crypt": "Theory",
        "log": "Theory",
        "bio": "Interdisciplinary Areas",
        "graph": "Interdisciplinary Areas",
        "csed": "Interdisciplinary Areas",
        "ecom": "Interdisciplinary Areas",
        "chi": "Interdisciplinary Areas",
        "robotics": "Interdisciplinary Areas",
        "visualization": "Interdisciplinary Areas"
    }

    # Areas in nextTier that should be ignored unless --include-next-tier is provided.
    next_tier = {
        'ase': True,
        'issta': True,
        'icde': True,
        'pods': True,
        'hpca': True,
        'ndss': True,
        'pets': True,
        'eurosys': True,
        'eurographics': True,
        'fast': True,
        'usenixatc': True,
        'icfp': True,
        'oopsla': True,
        'kdd': True,
    }

    # Theory areas: for these conferences the first author count is replaced by the weighted count.
    theory_areas = {"act", "crypt", "log"}

    # Load the ICLR points mapping from the pubs file.
    # Mapping: parent_area (lowercase) -> ICLR Points (float)
    iclr_points_mapping = {}
    try:
        with open(args.pubs_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parent = row["ParentArea"].strip().lower()
                try:
                    points = float(row["ICLR Points"])
                except ValueError:
                    continue
                iclr_points_mapping[parent] = points
    except Exception as e:
        sys.exit(f"Error reading ICLR points file: {e}")

    # Load the list of names from the provided names CSV.
    selected_names = set()
    try:
        with open(args.names, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                if name:
                    selected_names.add(name)
    except Exception as e:
        sys.exit(f"Error reading names CSV file: {e}")

    if not selected_names:
        sys.exit("No names found in the provided names CSV file.")

    # Totals per author: { author_name: {"first": total, "all": total, "weighted": total} }
    totals = {}
    # Tally of papers per candidate per parentparentarea:
    ppa_counts = {}

    # Process the publication report.
    try:
        with open(args.report, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["name"].strip()
                # Only process rows for authors in our input list.
                if name not in selected_names:
                    continue

                area = row["area"].strip().lower()
                # Skip if area is in nextTier and not including them.
                if area in next_tier and not args.include_next_tier:
                    continue

                try:
                    first_count = float(row["first_author_count"])
                    all_count = float(row["all_publication_count"])
                    weighted_count = float(row["weighted_publication_count"])
                except ValueError:
                    continue

                # Map the paper's area to its parent area.
                if area in parent_map:
                    parent_area = parent_map[area]
                else:
                    continue

                # Determine parent's parent's area.
                parent_parent = parent_parent_map.get(parent_area, "")
                if parent_parent:
                    if name not in ppa_counts:
                        ppa_counts[name] = {}
                    ppa_counts[name][parent_parent] = ppa_counts[name].get(parent_parent, 0) + 1

                # Only process further if we have ICLR points for the parent area.
                if parent_area not in iclr_points_mapping:
                    continue

                iclr_points = iclr_points_mapping[parent_area]

                # For theory areas, use weighted count for first-author points.
                if parent_area in theory_areas:
                    first_points = weighted_count * iclr_points
                else:
                    first_points = first_count * iclr_points

                all_points = all_count * iclr_points
                weighted_points = weighted_count * iclr_points

                if name not in totals:
                    totals[name] = {"first": 0.0, "all": 0.0, "weighted": 0.0}
                totals[name]["first"] += first_points
                totals[name]["all"] += all_points
                totals[name]["weighted"] += weighted_points
    except Exception as e:
        sys.exit(f"Error processing report CSV: {e}")

    # Write out the computed ICLR points totals per author.
    # For each candidate, determine the dominant parentparentarea (the one with the highest count).
    output_file = "iclr_points_report.csv"
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "name",
                "first_author_iclr_points",
                "all_author_iclr_points",
                "weighted_iclr_points",
                "parent_parent_area"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for author in sorted(selected_names):
                if author in totals:
                    first_val = totals[author]["first"]
                    all_val = totals[author]["all"]
                    weighted_val = totals[author]["weighted"]
                else:
                    first_val = 0.0
                    all_val = 0.0
                    weighted_val = 0.0

                # Determine dominant parentparentarea for this author.
                dominant_ppa = ""
                if author in ppa_counts and ppa_counts[author]:
                    # Select the parentparentarea with the highest publication count.
                    dominant_ppa = max(ppa_counts[author].items(), key=lambda x: x[1])[0]
                writer.writerow({
                    "name": author,
                    "first_author_iclr_points": f"{first_val:.5f}",
                    "all_author_iclr_points": f"{all_val:.5f}",
                    "weighted_iclr_points": f"{weighted_val:.5f}",
                    "parent_parent_area": dominant_ppa
                })
    except Exception as e:
        sys.exit(f"Error writing output CSV: {e}")

    print(f"ICLR points report generated: {output_file}")

if __name__ == "__main__":
    main()
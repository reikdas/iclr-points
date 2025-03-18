"""
Generate publication report for selected conferences.

Usage:
    python publication_report.py --names input_names.csv [--conference SUBSTRING]

The input CSV (specified via --names) should have a header with a column named "name".
The script processes dblp.xml.gz (which should be in the same directory) and for each publication
in selected conferences (with special handling as in the csrankings script) it calculates:
    - First-author count (if the first author is selected)
    - All-publication count (for every selected author appearing on the paper)
    - Weighted publication count (each selected author gets 1/number_of_authors)
for each (name, area, year) combination.
The output CSV file "publication_report.csv" will contain rows with these counts.
"""

import argparse
import gzip
import xmltodict
import csv
import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple, TypedDict

# Import definitions from the csrankings module.
from csrankings import (
    Area,
    Conference,
    areadict,
    TOG_SIGGRAPH_Volume,
    TOG_SIGGRAPH_Asia_Volume,
    CGF_EUROGRAPHICS_Volume,
    TVCG_Vis_Volume,
    TVCG_VR_Volume,
    map_pacmmod_to_conference,
)

# Define a TypedDict for a DBLP article.
class ArticleType(TypedDict, total=False):
    author: Any
    booktitle: str
    journal: str
    volume: str
    number: str
    url: str
    year: str
    pages: str
    title: Any

# Parse command-line arguments.
parser = argparse.ArgumentParser(
    description="Generate publication report (first-author, all, and weighted counts) for selected conferences."
)
parser.add_argument(
    "--names",
    type=str,
    required=True,
    help="CSV file containing a list of names (with a column 'name').",
)
parser.add_argument(
    "--conference",
    type=str,
    default="",
    help="Only use papers whose conference string contains this substring (default: all conferences).",
)
args = parser.parse_args()

# Load the set of selected names from the input CSV.
selected_names = set()
try:
    with open(args.names, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get("name", "").strip()
            if name:
                selected_names.add(name)
except Exception as e:
    sys.exit(f"Error reading names CSV file: {e}")

if not selected_names:
    sys.exit("No names found in the provided CSV file.")

# Build a mapping from conference abbreviations to their research area.
conference_area_mapping: Dict[str, str] = {}
for area, conf_list in areadict.items():
    for conf in conf_list:
        conference_area_mapping[conf] = area

# Dictionaries to hold counts.
# Keys are tuples: (name, area, year)
first_author_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
all_publication_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
weighted_publication_counts: Dict[Tuple[str, str, int], float] = defaultdict(float)

def get_author_list(article: ArticleType) -> List[str]:
    """
    Extract a list of author names from an article record.
    Handles cases where the "author" field is a list, a dict, or a string.
    """
    authors: List[str] = []
    if "author" not in article:
        return authors
    auth_field = article["author"]
    if isinstance(auth_field, list):
        for a in auth_field:
            if isinstance(a, dict):
                authors.append(a.get("#text", "").strip())
            else:
                authors.append(str(a).strip())
    elif isinstance(auth_field, dict):
        authors.append(auth_field.get("#text", "").strip())
    else:
        authors.append(str(auth_field).strip())
    return authors

def handle_article(_: Any, article: ArticleType) -> bool:
    """
    Process each article record from the dblp XML.
    Checks if the paper is from one of the selected conferences,
    applies special handling for certain areas, and if at least one author
    in the paper is in the selected names list, updates counts for:
      - All publications (for every selected author on the paper)
      - Weighted publications (each selected author gets a fraction of 1)
      - First-author publications (if the first author is selected)
    """
    authors = get_author_list(article)
    if not authors:
        return True

    # Determine the conference name.
    if "booktitle" in article:
        confname = Conference(article["booktitle"])
    elif "journal" in article:
        confname = Conference(article["journal"])
    else:
        return True

    # Apply conference filter if provided.
    if args.conference and args.conference not in confname:
        return True

    # Skip if conference is not in our mapping.
    if confname not in conference_area_mapping:
        return True

    # Get the initial area.
    area = conference_area_mapping[confname]

    # Extract publication details.
    try:
        year = int(article.get("year", "-1"))
    except ValueError:
        return True
    volume = article.get("volume", "0")
    number = article.get("number", "0")
    pages = article.get("pages", "")

    # Special handling for PACMPL and PACMSE.
    if area in [Area("pacmpl"), Area("pacmse")]:
        confname = Conference(article["number"])
        if confname in conference_area_mapping:
            area = conference_area_mapping[confname]
        else:
            return True
    # Special handling for PACMMOD.
    elif area == Area("pacmmod"):
        confname, year = map_pacmmod_to_conference(confname, year, number)
        if confname in conference_area_mapping:
            area = conference_area_mapping[confname]
        else:
            return True
    # Special handling for ACM Trans. Graph.
    elif confname == Conference("ACM Trans. Graph."):
        if year in TOG_SIGGRAPH_Volume:
            vol, num = TOG_SIGGRAPH_Volume[year]
            if volume == str(vol) and number == str(num):
                confname = Conference("SIGGRAPH")
                area = conference_area_mapping.get(confname, area)
        if year in TOG_SIGGRAPH_Asia_Volume:
            vol, num = TOG_SIGGRAPH_Asia_Volume[year]
            if volume == str(vol) and number == str(num):
                confname = Conference("SIGGRAPH Asia")
                area = conference_area_mapping.get(confname, area)
    # Special handling for Comput. Graph. Forum.
    elif confname == Conference("Comput. Graph. Forum"):
        if year in CGF_EUROGRAPHICS_Volume:
            vol, num = CGF_EUROGRAPHICS_Volume[year]
            if volume == str(vol) and number == str(num):
                confname = Conference("EUROGRAPHICS")
                area = conference_area_mapping.get(confname, area)
    # Special handling for IEEE Trans. Vis. Comput. Graph.
    elif confname == "IEEE Trans. Vis. Comput. Graph.":
        if year in TVCG_Vis_Volume:
            vol, num = TVCG_Vis_Volume[year]
            if volume == str(vol) and number == str(num):
                area = Area("vis")
        if year in TVCG_VR_Volume:
            vol, num = TVCG_VR_Volume[year]
            if volume == str(vol) and number == str(num):
                confname = Conference("VR")
                area = Area("vr")

    # Process the paper only if at least one author is in the selected names.
    if not any(author in selected_names for author in authors):
        return True

    num_authors = len(authors)

    # For every author in the paper who is selected, update all-publication and weighted counts.
    for author in authors:
        if author in selected_names:
            key = (author, area, year)
            all_publication_counts[key] += 1
            weighted_publication_counts[key] += 1.0 / num_authors

    # Additionally, update the first-author count if the first author is selected.
    if authors[0] in selected_names:
        key = (authors[0], area, year)
        first_author_counts[key] += 1

    return True

def main() -> None:
    # Process the dblp XML file.
    try:
        with gzip.open("dblp.xml.gz", "rb") as f:
            xmltodict.parse(f, item_depth=2, item_callback=handle_article)
    except Exception as e:
        sys.exit(f"Error processing dblp.xml.gz: {e}")

    # Combine keys from all count dictionaries.
    all_keys = set(first_author_counts.keys()) | set(all_publication_counts.keys()) | set(weighted_publication_counts.keys())

    output_file = "publication_report.csv"
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "name",
                "area",
                "year",
                "first_author_count",
                "all_publication_count",
                "weighted_publication_count",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            # Sort by name, then area, then year.
            for key in sorted(all_keys):
                name, area, year = key
                writer.writerow({
                    "name": name,
                    "area": area,
                    "year": year,
                    "first_author_count": first_author_counts.get(key, 0),
                    "all_publication_count": all_publication_counts.get(key, 0),
                    "weighted_publication_count": f"{weighted_publication_counts.get(key, 0):.5f}",
                })
    except Exception as e:
        sys.exit(f"Error writing report CSV: {e}")

    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import argparse
import contextlib
import gzip
import xmltodict
import csv
import sys
from collections import defaultdict
from typing import Any, Dict, List

# Import functions and constants from csrankings.
from csrankings import (
    Area,
    Conference,
    countPaper,
    pagecount,
    startpage,
    areadict,
    confdict,  # This maps raw conference names to canonical abbreviations.
    TOG_SIGGRAPH_Volume,
    TOG_SIGGRAPH_Asia_Volume,
    CGF_EUROGRAPHICS_Volume,
    TVCG_Vis_Volume,
    TVCG_VR_Volume,
    map_pacmmod_to_conference,
)

# Global dictionaries to accumulate candidate scores.
candidate_total: Dict[str, float] = defaultdict(float)
candidate_adjusted: Dict[str, float] = defaultdict(float)
candidate_first: Dict[str, float] = defaultdict(float)
# For each candidate, map parent area -> accumulated ICLR points.
candidate_parent: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

# Set of candidate names (from can_names.csv).
candidate_names = set()

# Mappings from conferences.csv:
#  - conf_to_area: conference abbreviation -> real research area.
#  - conf_to_parent: conference abbreviation -> parent area.
conf_to_area: Dict[str, str] = {}
conf_to_parent: Dict[str, str] = {}

# Mapping from research area to ICLR point (from iclr.csv).
area_to_iclr: Dict[str, float] = {}


def load_candidate_names(filename: str) -> None:
    with open(filename, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            name = row["name"].strip()
            if name:
                candidate_names.add(name)
    print(f"Loaded {len(candidate_names)} candidate names.")


def load_conferences(filename: str) -> None:
    global conf_to_area, conf_to_parent
    with open(filename, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            # Only consider conferences not marked as NextTier.
            if row["NextTier"].strip().lower() != "false":
                continue
            conf = row["Conference"].strip()
            area = row["Area"].strip()
            parent = row["ParentArea"].strip()
            conf_to_area[conf] = area
            conf_to_parent[conf] = parent
    print(f"Loaded mappings for {len(conf_to_area)} conferences.")


def load_iclr_points(filename: str) -> None:
    global area_to_iclr
    with open(filename, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            area = row["Area"].strip()
            try:
                point = float(row["ICLRPoint"])
            except ValueError:
                point = 0.0
            area_to_iclr[area] = point
    print(f"Loaded ICLR points for {len(area_to_iclr)} areas.")


def handle_article(_: Any, article: Dict[str, Any]) -> bool:
    try:
        # Get the raw conference name from the article.
        if "booktitle" in article:
            raw_conf = article["booktitle"].strip()
        elif "journal" in article:
            raw_conf = article["journal"].strip()
        else:
            return True

        # Use csrankings.confdict to translate raw conference name to a canonical abbreviation.
        # If not found, fall back to the raw name.
        if raw_conf in confdict:
            canonical_conf = confdict[raw_conf]
        else:
            canonical_conf = raw_conf

        # Get volume, number, and year.
        volume = article.get("volume", "0").strip()
        number = article.get("number", "0").strip()
        try:
            year = int(article.get("year", "-1").strip())
        except Exception:
            year = -1

        # --- Apply special processing on the canonical conference abbreviation ---
        if canonical_conf in ["pacmpl", "pacmse"]:
            # For PACMPL/PACMSE, try using the article's "number" field as the conference.
            new_conf = article.get("number", "").strip()
            if new_conf in conf_to_area:
                canonical_conf = new_conf
            else:
                return True
        elif canonical_conf == "pacmmod":
            # Use the provided mapping to translate pacmmod.
            canonical_conf, year = map_pacmmod_to_conference(
                canonical_conf, year, number
            )
        elif canonical_conf == "ACM Trans. Graph.":
            if year in TOG_SIGGRAPH_Volume:
                vol_expected, num_expected = TOG_SIGGRAPH_Volume[year]
                if volume == str(vol_expected) and number == str(num_expected):
                    canonical_conf = "SIGGRAPH"
            if year in TOG_SIGGRAPH_Asia_Volume:
                vol_expected, num_expected = TOG_SIGGRAPH_Asia_Volume[year]
                if volume == str(vol_expected) and number == str(num_expected):
                    canonical_conf = "SIGGRAPH Asia"
        elif canonical_conf == "Comput. Graph. Forum":
            if year in CGF_EUROGRAPHICS_Volume:
                vol_expected, num_expected = CGF_EUROGRAPHICS_Volume[year]
                if volume == str(vol_expected) and number == str(num_expected):
                    canonical_conf = "EUROGRAPHICS"
        elif canonical_conf == "IEEE Trans. Vis. Comput. Graph.":
            if year in TVCG_Vis_Volume:
                vol_expected, num_expected = TVCG_Vis_Volume[year]
                if volume == str(vol_expected) and number == str(num_expected):
                    canonical_conf = "vis"
            if year in TVCG_VR_Volume:
                vol_expected, num_expected = TVCG_VR_Volume[year]
                if volume == str(vol_expected) and number == str(num_expected):
                    canonical_conf = "VR"
        # ------------------------------------------------------------------------

        # Now translate the canonical conference abbreviation to a research area.
        if canonical_conf not in conf_to_area:
            return True
        real_area = conf_to_area[canonical_conf]
        iclr_point = area_to_iclr.get(real_area, 0.0)
        if iclr_point == 0.0:
            return True
        # Also get the parent area.
        parentArea = conf_to_parent.get(canonical_conf, "")

        # Process the list of authors.
        if "author" not in article:
            return True
        authors: List[str] = []
        if isinstance(article["author"], list):
            for a in article["author"]:
                if isinstance(a, dict):
                    name = a.get("#text", "").strip()
                else:
                    name = str(a).strip()
                if name:
                    authors.append(name)
        elif isinstance(article["author"], dict):
            authors.append(article["author"].get("#text", "").strip())
        elif isinstance(article["author"], str):
            authors.append(article["author"].strip())
        else:
            return True

        if not authors:
            return True

        num_authors = len(authors)

        # For each candidate in the author list, if the name is in candidate_names update scores.
        for idx, author in enumerate(authors):
            if author not in candidate_names:
                continue

            # (1) Total ICLR points: add full iclr_point.
            candidate_total[author] += iclr_point
            # (2) Adjusted ICLR points: add iclr_point divided by the number of authors.
            candidate_adjusted[author] += iclr_point / num_authors
            # (3) First author ICLR points:
            # For Theory conferences (parent area "Theory" case‐insensitive), award adjusted credit.
            if parentArea.lower() == "theory":
                candidate_first[author] += iclr_point / num_authors
            elif idx == 0:
                candidate_first[author] += iclr_point
            # (4) Accumulate by parent area.
            candidate_parent[author][parentArea] += iclr_point

    except Exception as e:
        print("Error processing article:", e, file=sys.stderr)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape dblp to compute candidate ICLR metrics."
    )
    parser.add_argument(
        "--candidates",
        type=str,
        default="can_names.csv",
        help="CSV file containing candidate names (default: can_names.csv)",
    )
    parser.add_argument(
        "--dblp",
        type=str,
        default="dblp.xml.gz",
        help="Path to dblp.xml.gz (default: dblp.xml.gz)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="candidate_iclr.csv",
        help="Output CSV file with candidate metrics (default: candidate_iclr.csv)",
    )
    args = parser.parse_args()

    load_candidate_names(args.candidates)
    load_conferences("conferences.csv")
    load_iclr_points("iclr.csv")

    print("Processing dblp data...")
    try:
        with gzip.open(args.dblp, "rb") as f:
            xmltodict.parse(f, item_depth=2, item_callback=handle_article)
    except Exception as e:
        print("Error processing dblp.xml.gz:", e, file=sys.stderr)
        sys.exit(1)

    # Determine, for each candidate, the parent area where they earned the most ICLR points.
    output_rows = []
    for cand in candidate_names:
        tot = candidate_total.get(cand, 0.0)
        adj = candidate_adjusted.get(cand, 0.0)
        first = candidate_first.get(cand, 0.0)
        par_dict = candidate_parent.get(cand, {})
        if par_dict:
            top_parent = max(par_dict.items(), key=lambda x: x[1])[0]
        else:
            top_parent = ""
        output_rows.append(
            {
                "name": cand,
                "TotalICLRPoints": tot,
                "AdjustedICLRPoints": adj,
                "FirstAuthorICLRPoints": first,
                "TopParentArea": top_parent,
            }
        )

    # Write the candidate metrics to a CSV file.
    fieldnames = [
        "name",
        "TotalICLRPoints",
        "AdjustedICLRPoints",
        "FirstAuthorICLRPoints",
        "TopParentArea",
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    print(f"Candidate ICLR metrics written to {args.output}")


if __name__ == "__main__":
    main()

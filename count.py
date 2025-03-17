import argparse
import gzip
import xmltodict
import csv
import sys
from collections import defaultdict
from csrankings import (
    Area,
    Conference,
    areadict,
    countPaper,
    map_pacmmod_to_conference,
    TOG_SIGGRAPH_Volume,
    TOG_SIGGRAPH_Asia_Volume,
    CGF_EUROGRAPHICS_Volume,
    TVCG_Vis_Volume,
    TVCG_VR_Volume,
)

# Build a mapping from conference name to its area (using areadict)
confdict = {}
for area, conf_list in areadict.items():
    for conf in conf_list:
        confdict[conf] = area

def pagecount(pages: str) -> int:
    if pages:
        parts = pages.split("-")
        if len(parts) == 2:
            try:
                start = int(parts[0])
                end = int(parts[1])
                return end - start + 1
            except ValueError:
                return -1
    return -1

def startpage(pages: str) -> int:
    if pages:
        parts = pages.split("-")
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                return -1
    return -1

def handle_article(article, conference_filter: str, counts: dict):
    # Skip records with no authors
    if "author" not in article:
        return True

    # Determine the conference name from the "booktitle" or "journal" field.
    if "booktitle" in article:
        confname = Conference(article["booktitle"])
    elif "journal" in article:
        confname = Conference(article["journal"])
    else:
        return True

    # If a conference filter is provided, only process matching entries.
    if conference_filter and (conference_filter not in confname):
        return True

    # Only consider publications in conferences that are in areadict.
    if confname not in confdict:
        return True

    try:
        year = int(article.get("year", "-1"))
    except ValueError:
        return True

    volume = article.get("volume", "0")
    number = article.get("number", "0")
    pages = article.get("pages", "")
    url = article.get("url", "")

    # Get the area associated with the conference.
    areaname = confdict[confname]

    # --- Special handling as in the original script ---
    if areaname == Area("pacmpl") or areaname == Area("pacmse"):
        confname = Conference(article["number"])
        if confname in confdict:
            areaname = confdict[confname]
        else:
            return True
    elif areaname == Area("pacmmod"):
        (confname, year) = map_pacmmod_to_conference(confname, year, number)
        areaname = confdict.get(confname, areaname)
    elif confname == Conference("ACM Trans. Graph."):
        if year in TOG_SIGGRAPH_Volume:
            (vol, num) = TOG_SIGGRAPH_Volume[year]
            if (volume == str(vol)) and (number == str(num)):
                confname = Conference("SIGGRAPH")
                areaname = confdict[confname]
        if year in TOG_SIGGRAPH_Asia_Volume:
            (vol, num) = TOG_SIGGRAPH_Asia_Volume[year]
            if (volume == str(vol)) and (number == str(num)):
                confname = Conference("SIGGRAPH Asia")
                areaname = confdict[confname]
    elif confname == Conference("Comput. Graph. Forum"):
        if year in CGF_EUROGRAPHICS_Volume:
            (vol, num) = CGF_EUROGRAPHICS_Volume[year]
            if (volume == str(vol)) and (number == str(num)):
                confname = Conference("EUROGRAPHICS")
                areaname = confdict[confname]
    elif confname == "IEEE Trans. Vis. Comput. Graph.":
        if year in TVCG_Vis_Volume:
            (vol, num) = TVCG_Vis_Volume[year]
            if (volume == str(vol)) and (number == str(num)):
                areaname = Area("vis")
        if year in TVCG_VR_Volume:
            (vol, num) = TVCG_VR_Volume[year]
            if (volume == str(vol)) and (number == str(num)):
                confname = Conference("VR")
                areaname = Area("vr")
    # ----------------------------------------------------------

    # Only count publications between 1970 and 2269.
    if year < 1970 or year > 2269:
        return True

    pcount = pagecount(pages)
    spage = startpage(pages)
    title = article.get("title", "")
    if isinstance(title, dict):
        title = title.get("#text", "")

    # Count the paper if it qualifies.
    if countPaper(confname, year, volume, number, pages, spage, pcount, url, title):
        counts[(areaname, year)] += 1

    return True

def main():
    parser = argparse.ArgumentParser(
        description="Create a CSV summarizing the number of publications per area per year from dblp.xml.gz"
    )
    parser.add_argument(
        "--conference",
        type=str,
        default="",
        help="If provided, only count publications for conferences that include this substring."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="area_publications.csv",
        help="Output CSV file name (default: area_publications.csv)."
    )
    args = parser.parse_args()

    # Dictionary to count publications by (area, year)
    counts = defaultdict(int)

    def callback(_, article):
        handle_article(article, args.conference, counts)
        return True

    try:
        with gzip.open("dblp.xml.gz", "rb") as gz:
            xmltodict.parse(gz, item_depth=2, item_callback=callback)
    except Exception as e:
        print("Error processing XML:", e, file=sys.stderr)
        sys.exit(1)

    # Write the aggregated counts to a CSV file.
    with open(args.output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Area", "Year", "PublicationCount"])
        # Sorting by area and then year for clarity.
        for (area, year), count in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1])):
            writer.writerow([area, year, count])

    print("CSV summary written to", args.output)

if __name__ == "__main__":
    main()
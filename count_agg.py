import argparse
import csv
from collections import defaultdict

# Parent mapping: maps a lower-case area to its parent.
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

# Areas listed in the nextTier (publications in these areas are ignored for now)
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

def main():
    parser = argparse.ArgumentParser(
        description="Map areas to parent areas and aggregate publication counts, ignoring next-tier areas."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="area_publications.csv",
        help="Input CSV file with columns Area, Year, PublicationCount (default: area_publications.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="parent_area_publications.csv",
        help="Output CSV file name (default: parent_area_publications.csv)"
    )
    args = parser.parse_args()

    # Dictionary to accumulate counts by (parent_area, year)
    aggregated = defaultdict(int)

    with open(args.input, newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            # Read and normalize the area name to lower-case
            area = row["Area"].strip().lower()
            year = row["Year"].strip()
            try:
                count = int(row["PublicationCount"])
            except ValueError:
                continue

            # Skip areas in next_tier.
            if area in next_tier:
                continue

            # Map the area to its parent; if not present, use the original area.
            parent = parent_map.get(area, area)
            aggregated[(parent, year)] += count

    # Write the aggregated results to the output CSV.
    with open(args.output, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["ParentArea", "Year", "PublicationCount"])
        # Sort by ParentArea (alphabetically) then by Year (numerically).
        for (parent, year), count in sorted(aggregated.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
            writer.writerow([parent, year, count])

    print("Aggregated parent area publication counts written to", args.output)

if __name__ == "__main__":
    main()
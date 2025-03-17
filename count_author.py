import argparse
import csv
from collections import defaultdict

# Parent mapping: maps a given area to its parent.
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

# Areas that should be ignored (next-tier areas)
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
        description="Aggregate faculty counts per parent area from generated-author-info.csv"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="generated-author-info.csv",
        help="Input CSV file (default: generated-author-info.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="faculty_parent_area_counts.csv",
        help="Output CSV file (default: faculty_parent_area_counts.csv)"
    )
    args = parser.parse_args()

    # Dictionary mapping faculty names to a set of unique parent areas they work in.
    faculty2areas = {}

    with open(args.input, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            name = row["name"].strip()
            area = row["area"].strip().lower()
            # Skip areas that belong to next-tier.
            if area in next_tier:
                continue
            # Map to parent area if available; otherwise, keep the area.
            parent = parent_map.get(area, area)
            if name not in faculty2areas:
                faculty2areas[name] = set()
            faculty2areas[name].add(parent)

    # Aggregate the fractional contributions.
    aggregated = defaultdict(float)
    for faculty, areas in faculty2areas.items():
        if not areas:
            continue
        contribution = 1.0 / len(areas)
        for parent in areas:
            aggregated[parent] += contribution

    # Write the aggregated counts to the output CSV.
    with open(args.output, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["ParentArea", "FacultyCount"])
        # Sorted alphabetically by parent area.
        for parent, count in sorted(aggregated.items()):
            writer.writerow([parent, count])

    print("Aggregated faculty counts written to", args.output)

if __name__ == "__main__":
    main()
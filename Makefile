all: fetch_data area_publications.csv

fetch_data:
	curl -o dblp.xml.gz https://csrankings.org/dblp.xml.gz
	curl -o generated-author-info.csv https://csrankings.org/generated-author-info.csv
	curl -o csrankings.py https://raw.githubusercontent.com/emeryberger/CSrankings/refs/heads/gh-pages/util/csrankings.py
	curl -o sigcse-research-articles.csv https://raw.githubusercontent.com/emeryberger/CSrankings/refs/heads/gh-pages/sigcse-research-articles.csv

area_publications.csv: dblp.xml.gz generated-author-info.csv csrankings.py sigcse-research-articles.csv
	python3 count.py

"""
Fetching helpers.

Source of truth:
- GPT4_Code.ipynb Cell 2: fetch_full_texts, fetch_abstracts
- GPT4_Code.ipynb Cell 4: query PMIDs from config keyword
- GPT4_Code.ipynb Cell 6: load PMIDs from pmid_file
"""

import time

from Bio import Entrez
from bs4 import BeautifulSoup


def fetch_full_texts(pmids, fetcher):
    """
    Fetch full texts from PMC XML.

    Copied closely from the notebook's fetch_full_texts function.
    """
    time.sleep(1)
    full_texts, titles = {}, {}

    print(f"Retrieved PMIDs: {pmids}")
    print(f"Number of PMIDs retrieved: {len(pmids)}")

    for pmid in pmids:
        try:
            article = fetcher.article_by_pmid(pmid)
            titles[pmid] = article.title

            pmcid = article.pmc
            if pmcid:# If there is a PMC ID, fetch the full text from PMC XML.
                handle = Entrez.efetch(db="pmc", id=pmcid, rettype="xml", retmode="xml")
                xml_data = handle.read()
                handle.close()
                # pass into BeautifulSoup to extract text from <p> and <sec> tags etc
                soup = BeautifulSoup(xml_data, features="xml")

                paragraphs = soup.find_all("p")
                sections = soup.find_all("sec")

                if paragraphs:
                    full_text = "\n".join(p.get_text() for p in paragraphs)
                else:
                    full_text = "\n".join(s.get_text() for s in sections)

                if full_text.strip():
                    full_texts[pmid] = full_text
                else:
                    full_texts[pmid] = "Full text unavailable"

            else:
                full_texts[pmid] = "Full text unavailable"

        except Exception as e:
            print(f"Error fetching full text for PMID {pmid}: {e}")
            titles[pmid] = titles.get(pmid, "Unavailable")
            full_texts[pmid] = "Full text unavailable"

    return titles, full_texts


def fetch_abstracts(pmids, fetcher):
    """
    Fetch abstracts from PubMed.

    Copied closely from the notebook's fetch_abstracts function.
    """
    abstracts = {}
    titles = {}

    for pmid in pmids:
        try:
            article = fetcher.article_by_pmid(pmid)
            titles[pmid] = article.title
            abstracts[pmid] = article.abstract if article.abstract else "Abstract unavailable"

        except Exception as e:
            print(f"Error fetching abstract for PMID {pmid}: {e}")
            titles[pmid] = titles.get(pmid, "Unavailable")
            abstracts[pmid] = "Abstract unavailable"

    return titles, abstracts

##Keyword search mode helpers
def get_pmids_from_query_config(config, fetcher):
    
    pmids = []
    keyword = None
    output_file = None

    if "queries" in config:
        for query in config["queries"]:
            keyword = query["keyword"]
            output_file = query["output_file"]

            candidate_count = config["num_of_articles"] * 2
            pmids = fetcher.pmids_for_query(
                f"{keyword} AND pubmed pmc open access[filter]",
                retmax=candidate_count
            )

            print(pmids)

            # Writes the queried PMIDs to a txt file.
            with open("pmids_queried.txt", "w") as f:
                for pmid in pmids:
                    f.write(pmid + "\n")

    else:
        print("No queries found in the configuration file.")

    return pmids, keyword, output_file

##Manual PMID input mode helper
def load_pmids_from_config_file(config):
    
    if "pmid_file" not in config:
        return []

    pmid_file = config["pmid_file"]

    try:
        pmids = []
        with open(pmid_file, "r") as f:
            for line in f:
                if line.strip():
                    pmids.append(line.strip())
    
    except FileNotFoundError:
        print(f"PMID file \"{pmid_file}\" not found; will use keyword search.")
        return []

    if pmids:
        print(f"Loaded {len(pmids)} PMIDs from \"{pmid_file}\".")
    else:
        print(f"PMID file \"{pmid_file}\" is empty; will use keyword search.")

    return pmids

## Overview

This pipeline turns papers from PubMed/PMC into lay summaries that a general reader can follow.
It does this by generating two independent summaries of every article: one from the PMC full text and one from the PubMed abstract, and grounding every claim in a specific, traceable piece of the source. The full-text summarizer cites individual paragraphs; the abstract summarizer cites individual sentences. Each summary is then scored across 6 metrics that measure their  readability and accuracy. The result is a set of CSVs containing the summaries, the readability scores, and a full audit trail showing which parts of the paper the model actually drew on.

## Key features:
1.  Load config and API keys.
2.  Load PMIDs from pmid_file, or fall back to a PubMed keyword search.
3.  Print article info (title, authors, journal).
4.  Fetch full text; keep only articles with full text and truncate to num_of_articles.
5.  Build paragraph-level citation evidence tables from PMC XML.
6.  Generate citation-aware full-text summaries.
7.  Strip citations to create metric-ready full-text summaries.
8.  Fetch abstracts and build sentence-level evidence tables.
9.  Generate citation-aware abstract summaries.
10. Strip citations to create metric-ready abstract summaries.
11. Compute similarity, readability (Flesch, SMOG, Gunning Fog), and RAGAS scores.
12. Merge into the final CSV and write the two evidence source tables.


## Citation workflow

The source is split into citable units — paragraphs for full text, sentences for abstracts — each given a sequential ID (`E1`, `E2`, …) and a readable label (`Results, para. 2`). The model sees only the IDs and marks claims with `[E4]`. Python resolves those markers afterwards by lookup against the table.

Because the model can only emit an ID that either exists or doesn't, an invented citation fails the lookup: it is dropped from the text and recorded in `invalid_evidence_ids`. Fabrication degrades to no citation rather than to a plausible wrong one.

Citations are stripped before metrics are computed, and a `used_in_summary` flag on the exported evidence table shows what the model actually drew on.

## Getting Started

### Prerequisites

- Python 3.8+
- An OpenAI API key (set as the `OPENAI_API_KEY` environment variable or in a `.env` file). We suggest using [shell-secrets](https://github.com/waj/shell-secrets) to encrypt your environment variables
- A registered Entrez Email and API key (set within "config.json"). For more info: [How do I obtain an API Key through an NCBI account?](https://support.nlm.nih.gov/kbArticle/?pn=KA-05317)
- A `config.json` file with summarization settings (see below for example)

### Installation

Install required packages:

```sh
pip install -r requirements.txt
```

### Configuration

Edit the `config.json` file to set the number of articles to be queried from PubMed, your Entrez API details, search keyword etc. *Include key "pmid_file" only if you have a defined list of PMIDs you would like to summarize.* Example:

```json
{
  "num_of_articles": 10,
  "max_summary_length": 350,
  "min_summary_length": 250,
  "entrez_email": "your_email@example.com",
  "entrez_api_key": "YOUR_NCBI_API_KEY",
  "output_directory":"./output",
  "queries": [
    {
      "keyword": "renal cancer",
      "output_file": "renal_cancer.csv"
    }
  ],
  "pmid_file": "pmids_to_summarize.txt"
}
```

### Usage

1. **Set your OpenAI API key**  
   Create a `.env` file and enter:
   ```sh
   OPENAI_API_KEY=sk-...
   ```

2. **Switching from Keyword Search to Manual PMID Input**

    Create a new text file in your project folder (e.g., pmids_to_summarize.txt). Add one PubMed ID (PMID) per line:

```json
{
  "num_of_articles": 10,
  "max_summary_length": 350,
  "min_summary_length": 250,
  "entrez_email": "your_email@example.com",
  "entrez_api_key": "YOUR_NCBI_API_KEY",
  "output_directory":"./output",
  "pmid_file":"FILE'S DIRECTORY"
  "queries": [
    {
      "keyword": "renal cancer",
      "output_file": "renal_cancer.csv"
    }
  ],
  "pmid_file": "pmids_to_summarize.txt"
}
```
    Start the script. The summarizer will automatically process only the PMIDs listed in your text file, bypassing keyword search.

3. **Run the program**  
    Click on top right corner "Run Python File" or 
    ```bash
    uv run python run_pipeline.py
    ```

4. **Outputs**  
   - Summaries and metrics are saved in the `output/` directory as CSV files.
   - You can adjust keywords, number of articles, and other settings in `config.json`.



### Streamlit interface Usage

Launch the interface from the terminal:

```bash
uv run streamlit run app_interface.py
```

Streamlit will open the interface in your default browser.

### Static site export

The summarizer must be run through the Streamlit interface first — this writes the
frozen summary data to `frozen_results/` inside the output directory.

Once that data exists, build the site:

```bash
uv run python build_static_site-2.py
```

This generates a set of HTML files in `site/`, also within the output directory. Deploy
that folder to Netlify (or any static host).
---



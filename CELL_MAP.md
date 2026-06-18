# Notebook Cell Map

This refactor uses the newly uploaded `GPT4_Code.ipynb` as the source of truth.

The goal is **not** to redesign the project. The goal is to move the notebook workflow into importable Python files with the smallest necessary changes.

## Cell 0 — installs and imports

Notebook role:
- Installs packages with `!python3 -m pip install ...`
- Imports pandas, OpenAI, Entrez, BeautifulSoup, RAGAS, sklearn, textstat, asyncio, etc.

Python-file role:
- Package installation is not inside Python modules.
- Dependencies stay in `requirements.txt`.
- Imports are moved into the files that need them.

Files affected:
- `src/lay_summary/config.py`
- `src/lay_summary/fetch.py`
- `src/lay_summary/summarize.py`
- `src/lay_summary/citations.py`
- `src/lay_summary/metrics.py`
- `src/lay_summary/pipeline.py`

## Cell 1 — config and API setup

Notebook role:
- Loads `OPENAI_API_KEY`
- Creates OpenAI client
- Loads `config.json`
- Reads `num_of_articles`, `max_summary_length`, `min_summary_length`, and `output_directory`
- Sets Entrez email and API key
- Creates `PubMedFetcher()`

Python-file location:
- `src/lay_summary/config.py`

Important functions:
- `load_project_config`
- `load_openai_api_key`
- `setup_openai_client`
- `setup_pubmed_fetcher`
- `print_config_summary`

## Cell 2 — original helper functions

Notebook role:
- `fetch_full_texts`
- `fetch_abstracts`
- `async_summarize`
- `gpt4_summarize_async`
- `compute_readability`
- `compute_ragas_faithfulness`

Python-file locations:
- `src/lay_summary/fetch.py`
  - `fetch_full_texts`
  - `fetch_abstracts`
- `src/lay_summary/summarize.py`
  - `async_summarize`
  - `gpt4_summarize_async`
- `src/lay_summary/metrics.py`
  - `compute_readability`
  - `compute_ragas_faithfulness`

Small necessary change:
- The notebook used a global `async_client`.
- The Python version uses `set_async_client(openai_api_key)` so the module can be imported cleanly.

## Cell 3 — markdown explanation for keyword query

Notebook role:
- Explains the keyword query section.

Python-file location:
- Explanation only. No code moved.

## Cell 4 — query PubMed by keyword

Notebook role:
- Uses `config["queries"]`
- Gets PMIDs using:
  `keyword AND pubmed pmc open access[filter]`
- Writes PMIDs to `pmids_queried.txt`

Python-file location:
- `src/lay_summary/fetch.py`

Function:
- `get_pmids_from_query_config`

## Cell 5 — markdown explanation for pmid_file

Notebook role:
- Explains loading PMIDs from a text file.

Python-file location:
- Explanation only. No code moved.

## Cell 6 — load PMIDs from pmid_file

Notebook role:
- If `pmid_file` exists in config, load PMIDs from that file.

Python-file location:
- `src/lay_summary/fetch.py`

Function:
- `load_pmids_from_config_file`

Important:
- This preserves the notebook behavior where loading `pmid_file` can overwrite PMIDs that were just queried.

## Cell 7 — base citation helper cell

Notebook role:
- Citation cleaning
- Section normalization
- PMC XML paragraph extraction
- Evidence table construction
- Evidence block formatting
- Evidence-ID to readable-citation conversion
- Citation-aware summary generation

Python-file location:
- `src/lay_summary/citations.py`

Important:
- Some functions from Cell 7 are patched/redefined by Cell 8.
- The Python file keeps the final patched behavior.

## Cell 8 — citation patch cell

Notebook role:
- Reduces crowded citations
- Replaces functions such as:
  - `citation_choose_best_evidence_id`
  - `citation_convert_evidence_ids_to_readable_citations`
  - `citation_collapse_adjacent_readable_citations`
  - `citation_summarize_one_article_async`

Python-file location:
- `src/lay_summary/citations.py`

Important:
- The test-running part at the bottom of Cell 8 was not moved into the main pipeline because Cell 9 is the integrated final workflow.
- The patched functions themselves are included.

## Cell 9 — integrated citation-aware main summarization section

Notebook role:
- This is the current main workflow.
- It replaces the old main summarization section.
- It does:
  1. Print article info
  2. Fetch full text
  3. Build citation evidence tables
  4. Generate cited full-text summaries
  5. Remove citation parentheses for metrics
  6. Generate abstract summaries
  7. Compute similarity
  8. Compute readability
  9. Compute RAGAS faithfulness
  10. Build final CSV
  11. Save citation source table CSV

Python-file location:
- `src/lay_summary/pipeline.py`

Small necessary change:
- Top-level `await` cannot be used directly in a `.py` script.
- So the workflow is wrapped in:
  - `async def run_pipeline_async(...)`
  - `def run_pipeline(...)`

## Cell 10 — old/original main summarization section

Notebook role:
- Original non-citation main summarization section.

Python-file status:
- Not used as the main workflow because Cell 9 says it replaces the original main summarization section.
- Its logic is still partly preserved through helper functions and metrics code:
  - abstract summaries
  - full-text availability
  - similarity
  - readability
  - RAGAS
  - CSV output

## How files connect

```text
run_pipeline.py
↓
src/lay_summary/pipeline.py
↓
config.py loads config/API keys
↓
fetch.py gets PMIDs, abstracts, full texts
↓
citations.py builds evidence tables and cited summaries
↓
summarize.py generates abstract summaries
↓
metrics.py calculates similarity/readability/RAGAS
↓
pipeline.py builds and saves output CSVs
```

## How to run

From the project root:

```bash
cp .env.example .env
```

Edit `.env`:

```text
OPENAI_API_KEY=sk-your-real-key
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
PYTHONPATH=src python run_pipeline.py
```

Or install the package in editable mode:

```bash
pip install -e .
python run_pipeline.py
```

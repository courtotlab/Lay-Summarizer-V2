## Overview

This project is a Python/Jupyter Notebook-based pipeline for retrieving biomedical research articles from PubMed, and generating lay summaries using AI. It fetches full texts and abstracts according to PubMed IDs (PMIDs), generates lay summaries using OpenAI-based LLMs, and computes various metrics such as readability, grade level, and faithfulness of summaries (using RAGAS). The results are saved as CSV files for further analysis.

Key features:
- Fetches articles by keyword or from a list of PMIDs.
- Summarizes abstracts and full texts for a lay audience.
- Calculates readability (Flesch Reading Ease, Flesch-Kincaid Grade).
- Computes similarity between abstract and full text summaries.
- Evaluates summary faithfulness using RAGAS.
- Outputs results to CSV files.

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
   Export your key or use a `.env` file:
   ```sh
   export OPENAI_API_KEY=sk-...
   ```

2. **Run the notebook**  
   Open `GPT4_Code.ipynb` in VS Code or Jupyter and run the cells.

3. **Outputs**  
   - Summaries and metrics are saved in the `output/` directory as CSV files.
   - You can adjust keywords, number of articles, and other settings in `config.json`.

---



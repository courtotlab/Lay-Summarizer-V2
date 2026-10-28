import asyncio
from datetime import datetime
import numpy as np
import pandas as pd
from src.lay_summary.config import load_project_config, setup_pubmed_fetcher
from src.lay_summary.fetch import fetch_abstracts, fetch_full_texts
from src.lay_summary.metrics import compute_ragas_summarization_score

model = "gpt-5.1"  # Specify the model you want to use for evaluation

async def evaluate_ragas_summarization_from_csv():
    config = load_project_config("./config.json")
    fetch = setup_pubmed_fetcher(config)

    input_csv_path = "/Users/t2yu/Desktop/2026-Lay-Summaries/Plot-R/Lay_summary_human_review_tracking - Summaries Data Original_- substituted&NewRAGAS copy.csv"
    df = pd.read_csv(input_csv_path)

    pmid_col = "pmid"
    df[pmid_col] = df[pmid_col].astype(str)
    pmids = df[pmid_col].to_list()

    print(f"Loaded {len(pmids)} PMIDs")

    # Define tasks: column name, fetch function for source reference text, and output column prefix
    eval_tasks = [
        {
            "summary_col": "Abstract_Summary_Without_In_Text_Citations",
            "fetch_func": fetch_abstracts,
            "prefix": "Abstract_RAGAS_Summarization",
        },
        {
            "summary_col": "Full_Text_Summary_Without_In_Text_Citations",
            "fetch_func": fetch_full_texts,
            "prefix": "FullText_RAGAS_Summarization",
        },
    ]

    num_replicates = 5

    for task in eval_tasks:
        summary_col = task["summary_col"]
        fetch_func = task["fetch_func"]
        prefix = task["prefix"]

        print(f"\n==========================================")
        print(f"Processing column: {summary_col}")
        print(f"==========================================")

        # 1. Fetch reference texts once per category (Abstracts or Full Texts)
        print(f"Fetching source reference texts using {fetch_func.__name__}...")
        _, reference_texts = fetch_func(pmids, fetch)

        # Create mapping of PMID -> summary text
        responses_dict = dict(zip(df[pmid_col], df[summary_col]))

        rep_columns = []
        
        # 2. Loop through 5 replicates
        for rep in range(1, num_replicates + 1):
            rep_col_name = f"{prefix}_Rep_{rep}"
            rep_columns.append(rep_col_name)

            print(f"-> Running Replicate {rep}/{num_replicates} for {summary_col}...")
            scores_dict = await compute_ragas_summarization_score(
                responses=responses_dict,
                references=reference_texts,
                model=model
            )

            # Map raw replicate score to the dataframe
            df[rep_col_name] = df[pmid_col].map(scores_dict)

        # 3. Compute row-wise Mean and Standard Deviation across the 5 replicates
        df[f"{prefix}_Mean"] = df[rep_columns].mean(axis=1)
        df[f"{prefix}_Std"] = df[rep_columns].std(axis=1)

    # Output CSV containing all individual raw replicates + calculated statistics
    output_csv_path = f"/Users/t2yu/Desktop/2026-Lay-Summaries/Plot-R/50_articles_with_replicated_ragas_scores_{model}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
    print(f"\nSuccessfully saved results with raw replicate data to: {output_csv_path}")


if __name__ == "__main__":
    asyncio.run(evaluate_ragas_summarization_from_csv())
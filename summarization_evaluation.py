import pandas as pd
import asyncio
from src.lay_summary.config import load_project_config, setup_pubmed_fetcher
from src.lay_summary.fetch import fetch_full_texts, fetch_abstracts
from src.lay_summary.metrics import compute_ragas_summarization_score


async def evaluate_ragas_summarization_from_csv():

    config = load_project_config("./config.json")
    fetch = setup_pubmed_fetcher(config)
    
    input_csv_path = "Lay_summary_human_review_tracking - Sum. Rerun.csv" 
    df = pd.read_csv(input_csv_path)

    pmid_col = "PMID"
    summary_col = "Abstract Summary" # changable

    df[pmid_col] = df[pmid_col].astype(str)

    pmids = df[pmid_col].to_list()
    summary = dict(zip(df[pmid_col], df[summary_col]))

    print(f"Loaded {len(pmids)} PMIDS")

    _, full_texts_reference = fetch_abstracts(pmids, fetch) # fetch raw text

    scores_dict = await compute_ragas_summarization_score(
        responses=summary,
        references=full_texts_reference,
        model="gpt-4.1")

    df["New_RAGAS_Summarization_Score"] = df[pmid_col].map(scores_dict)
    output_csv_path = "50_articles_with_updated_abstract_summarization_score rerun.csv"
    df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    asyncio.run(evaluate_ragas_summarization_from_csv())



        
        

        
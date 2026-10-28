import asyncio
from datetime import datetime
import inspect
import numpy as np
import pandas as pd
from src.lay_summary.config import load_project_config, setup_pubmed_fetcher
from src.lay_summary.fetch import fetch_abstracts, fetch_full_texts
from src.lay_summary.metrics import (
    compute_ragas_faithfulness,
    compute_ragas_summarization_score,
)

# Configuration Constants
MODEL = "gpt-5.1"
NUM_REPLICATES = 5
INPUT_CSV_PATH = (
    "/Users/t2yu/Desktop/2026-Lay-Summaries/Plot-R/"
    "First10.csv"
)

FAITHFULNESS_PROMPT = """You are writing a lay summary of a cancer research article.

Write one clear summary in 100 to {max_length} words.

Use only the evidence blocks. Do not add or infer unsupported details.

Audience and style:
Write for a non-scientist adult at grade 5th grade reading level. Use plain language that is easy to follow, but do not sound childish, patronizing, or overly simplified. 
Use clear, natural, respectful language and a calm, objective tone. Each sentence must be within 20 words.

Explain the cancer topic directly, as if calmly telling the reader what is happening. Do not refer to the article, paper, authors, publication, or evidence blocks as objects. Avoid phrases such as “the authors found,” “the article says,” “the paper reports,” “this study shows,” or “the publication describes.” Use “researchers” only when needed to describe what was done, such as “Researchers tested blood samples” or “Researchers reviewed past studies.”

Make the summary sound natural, like a clear explanation from a careful person. Avoid stiff, mechanical, or formulaic phrasing. Reduce any sentence that contain technical terms which will not help the readers to understand more about the summary.
Place citations BEFORE punctuations/full stops/periods and right after the ending word. eg: end [E1]. where [E1] is ahead of . and after "end".


Structure the summary to cover:
- What the research is about
- What the researchers did, briefly
- What they found, including numbers if clear
- Why the findings matter, with realistic impact and no exaggeration
-End with 1–2 short sentences on possible future clinical use or patient impact, only if supported by evidence.

Opening rule:
Do not begin with “This research looks at…” or any repeated template phrase. Start with a specific, natural sentence about the study topic. Vary the first sentence across summaries.

Language rules:
- Use short, clear sentences and mostly simple words, and each sentence must be within 20 words.
- Assume audience has no biology knowledge, avoid jargon, acronyms, and technical lists, even terms like RNA.
-Avoid using technical genes names such as ROS1, BRAF, MET, etc.
- Prefer plain phrases (e.g., “a gene change”, “a lab test”)
- Use mostly 1- to 3-syllable words. Avoid 4-syllable or longer words unless they are necessary medical or scientific terms, and explain them simply if used.
- Add a simple example if it improves clarity

Before returning, silently check that the summary follows the required structure, uses simple language, avoids unnecessary jargon, and complies with all citation rules. Revise if needed.

Citation rules:
- Use only evidence IDs (e.g., [E1])
- Use 3–5 citations total
- Do not cite every sentence
-Each sentence MUST contain exactly one citation at most.
-If multiple evidence blocks support a sentence: rewrite the sentence OR split into multiple sentences, each with only one citation.
- Do not repeat IDs unless needed
- Place citations before full stops (e.g., [E1])

Return only one clean lay summary.

Evidence blocks:
{evidence_text}
"""


async def _run_faithfulness(summaries, references, prompt, model):
    """Safely executes compute_ragas_faithfulness whether it is async or synchronous."""
    res = compute_ragas_faithfulness(
        summaries=summaries, references=references, prompt=prompt, model=model
    )
    if inspect.isawaitable(res):
        return await res
    return res


async def evaluate_ragas_combined_from_csv():
    config = load_project_config("./config.json")
    fetch = setup_pubmed_fetcher(config)

    df = pd.read_csv(INPUT_CSV_PATH)

    # Robust PMID column lookup
    pmid_col = next(
        (c for c in df.columns if c.strip().lower() == "pmid"), "pmid"
    )
    df[pmid_col] = df[pmid_col].astype(str)
    pmids = df[pmid_col].to_list()

    print(f"Loaded {len(pmids)} PMIDs from {INPUT_CSV_PATH}")

    eval_tasks = [
        {
            "summary_col": "Abstract_Summary_Without_In_Text_Citations",
            "fetch_func": fetch_abstracts,
            "prefix": "Abstract_RAGAS",
        },
        {
            "summary_col": "Full_Text_Summary_Without_In_Text_Citations",
            "fetch_func": fetch_full_texts,
            "prefix": "FullText_RAGAS",
        },
    ]

    for task in eval_tasks:
        summary_col = task["summary_col"]
        fetch_func = task["fetch_func"]
        prefix = task["prefix"]

        print(f"\n=======================================================")
        print(f"Processing Task: {summary_col}")
        print(f"=======================================================")

        # 1. Fetch source reference texts once per condition
        print(f"Fetching source reference texts using {fetch_func.__name__}...")
        _, reference_texts = fetch_func(pmids, fetch)

        # Dictionary mapping: PMID -> summary string
        summaries_dict = dict(zip(df[pmid_col], df[summary_col]))

        # Track replicate column names for summary stats
        summ_rep_cols = []
        faith_rep_cols = []

        # Dictionaries to buffer replicate data before assigning to df
        summ_data = {}
        faith_data = {}

        # 2. Run replicates
        for rep in range(1, NUM_REPLICATES + 1):
            summ_col_name = f"{prefix}_Summarization_Rep_{rep}"
            faith_col_name = f"{prefix}_Faithfulness_Rep_{rep}"
            summ_rep_cols.append(summ_col_name)
            faith_rep_cols.append(faith_col_name)

            print(
                f"-> Running Replicate {rep}/{NUM_REPLICATES} for {prefix}..."
            )


            # Metric A: Faithfulness Score
            faith_scores = await _run_faithfulness(
                summaries=summaries_dict,
                references=reference_texts,
                prompt=FAITHFULNESS_PROMPT,
                model=MODEL,
            )
            faith_data[faith_col_name] = df[pmid_col].map(faith_scores)


            # Metric B: Summarization Score
            summ_scores = await compute_ragas_summarization_score(
                responses=summaries_dict,
                references=reference_texts,
                model=MODEL,
            )
            summ_data[summ_col_name] = df[pmid_col].map(summ_scores)


        # 3. Assign Faithfulness block (Rep 1–5, Mean, Std)
        for col in faith_rep_cols:
            df[col] = faith_data[col]
        df[f"{prefix}_Faithfulness_Mean"] = df[faith_rep_cols].mean(axis=1)
        df[f"{prefix}_Faithfulness_Std"] = df[faith_rep_cols].std(axis=1)
            
        # 4. Assign Summarization block (Rep 1–5, Mean, Std)
        for col in summ_rep_cols:
            df[col] = summ_data[col]
        df[f"{prefix}_Summarization_Mean"] = df[summ_rep_cols].mean(axis=1)
        df[f"{prefix}_Summarization_Std"] = df[summ_rep_cols].std(axis=1)


    # 5. Save consolidated dataframe
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_csv_path = (
        f"/Users/t2yu/Desktop/2026-Lay-Summaries/Plot-R/"
        f"50_articles_combined_ragas_scores_{MODEL}_{timestamp}.csv"
    )
    df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
    print(f"\nAll tasks complete. Saved master output to:\n{output_csv_path}")


if __name__ == "__main__":
    asyncio.run(evaluate_ragas_combined_from_csv())
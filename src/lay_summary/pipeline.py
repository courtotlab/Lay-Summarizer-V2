"""
Main pipeline.

Source of truth:
- GPT4_Code.ipynb Cell 9:
  "MAIN SUMMARIZATION SECTION WITH CITATION INTEGRATION"

Minimal changes:
- Wrapped the notebook's top-level code in async function run_pipeline_async().
- Added run_pipeline() so run_pipeline.py can execute it.
- Kept the same variable flow and output column names.
"""

import asyncio
import os
from datetime import datetime
from functools import reduce
from pathlib import Path

import pandas as pd

from .citations import (
    citation_extract_evidence_table_for_one_pmid,
)
from .config import (
    load_openai_api_key,
    load_project_config,
    print_config_summary,
    setup_openai_client,
    setup_pubmed_fetcher,
)
from .fetch import (
    fetch_abstracts,
    fetch_full_texts,
    get_pmids_from_query_config,
    load_pmids_from_config_file,
)
from .metrics import (
    calculate_smog_index,
    calculate_gunning_fog_score,
    clean_summary_text,
    compute_ragas_faithfulness,
    compute_readability,
    evaluate_similarity,
    remove_citation_parentheses,
    compute_ragas_summarization_score)

from .summarize import (
    abstract_citation_summarize_many_article_async,
    citation_summarize_many_articles_async,
    set_async_client as set_summary_async_client,
)


async def run_pipeline_async(config_path="./config.json"):
    """
    Run the whole lay-summary pipeline.

    This fun1nfig and API keys.
    2. Query PubMed for PMIDs.
    3. Optionally load PMIDs from pmid_file.
    4. Print article information.
    5. Fetch full text.
    6. Build citation evidence tables.
    7. Generate citation-aware full-text summaries.
    8. Create citation-free summaries for metrics.
    9. Generate abstract summaries.
    10. Compute similarity, readability, and RAGAS faithfulness.
    11. Build final CSV.
    12. Save citation source table CSV.
    """
    openai_api_key = load_openai_api_key()

    # Regular client is created to preserve the notebook setup,
    # even though the async functions use AsyncOpenAI.
    client = setup_openai_client(openai_api_key)
    _ = client

    config = load_project_config(config_path)

    num_of_articles = config["num_of_articles"]
    max_summary_length = config["max_summary_length"]
    min_summary_length = config["min_summary_length"]
    output_directory = config["output_directory"]

    _ = num_of_articles
    _ = min_summary_length

    fetch = setup_pubmed_fetcher(config)
    print_config_summary(config)

    set_summary_async_client(openai_api_key)

    # ------------------------------------------------------------
    # PMID resolution: file takes priority over keyword search.
    #
    # If pmid_file exists and contains valid IDs, use them directly.
    # Otherwise fall back to a keyword search, which also writes
    # the found IDs back to pmid_file for traceability.
    # ------------------------------------------------------------
    keyword = None
    output_file = None

    pmids_from_file = load_pmids_from_config_file(config)

    if pmids_from_file:
        pmids = pmids_from_file
    else:
        pmids, keyword, output_file = get_pmids_from_query_config(config, fetch)

    if not pmids:
        raise ValueError("No PMIDs were found. Check config.json queries or pmid_file.")

    # ------------------------------------------------------------
    # 2. Print article information
    # ------------------------------------------------------------
    print("Article information:")
    print("--------------------")

    for pmid in pmids:
        try:
            article = fetch.article_by_pmid(pmid)
            print(f"PMID {pmid}: {article.title}")
            print(f"Authors: {', '.join([str(a) for a in article.authors])}")
            print(f"Journal: {article.journal}")
            print("---")

        except Exception as error:
            print(f"Could not print article info for PMID {pmid}: {error}")
            print("---")

    # ------------------------------------------------------------
    # 3. Fetch full text as raw text
    # ------------------------------------------------------------
    titles_from_full_text, full_texts = fetch_full_texts(pmids, fetch)

    available_pmids = []

    for pmid in pmids:
        if full_texts.get(pmid) != "Full text unavailable":
            available_pmids.append(pmid)

    requested_number = config["num_of_articles"]

    pmids = available_pmids[:requested_number]

    titles_from_full_text = {
        pmid: titles_from_full_text[pmid]
        for pmid in pmids
    }

    full_texts = {
        pmid: full_texts[pmid]
        for pmid in pmids
    }

    print(f"Requested articles: {requested_number}")
    print(f"Available full-text articles selected: {len(pmids)}")
    print(f"Final PMIDs used: {pmids}")

    if len(pmids) < requested_number:
        print(
            f"Warning: only found {len(pmids)} available full-text articles "
            f"from the candidate pool."
        )

    # ------------------------------------------------------------
    # 4. Fetch PMC XML as paragraph-level citation evidence
    # ------------------------------------------------------------
    article_metadata = {}
    citation_source_tables = {}

    print("\nBuilding citation evidence tables...")
    print("------------------------------------")

    for pmid in pmids:
        try:
            title, pmcid, source_table = citation_extract_evidence_table_for_one_pmid(
                pmid=pmid,
                fetcher=fetch
            )

            article_metadata[pmid] = {
                "title": title,
                "pmcid": pmcid,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }

            citation_source_tables[pmid] = source_table

            print(
                f"PMID {pmid}: extracted {len(source_table)} citation evidence paragraphs."
            )

        except Exception as error:
            print(f"Error building citation table for PMID {pmid}: {error}")

            article_metadata[pmid] = {
                "title": titles_from_full_text.get(pmid, "Title unavailable"),
                "pmcid": None,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }

            citation_source_tables[pmid] = pd.DataFrame()

    # ------------------------------------------------------------
    # 5. Generate citation-aware full-text summary
    # ------------------------------------------------------------
    print("\nGenerating citation-aware full-text summaries...")
    print("------------------------------------------------")

    citation_summary_results = await citation_summarize_many_articles_async(
        article_metadata=article_metadata,
        source_tables=citation_source_tables,
        max_length=max_summary_length,
        prompt_file_path=Path(__file__).resolve().parents[2] / "full_summarizer_prompt",
        concurrency=5,
        model_name="gpt-5.1"
    )

    full_text_summaries_with_citations = {}

    for pmid in citation_summary_results:
        full_text_summaries_with_citations[pmid] = clean_summary_text(citation_summary_results[pmid][
            "summary_with_readable_citations"
        ])

    # ------------------------------------------------------------
    # 6. Create citation-free full-text summary for metrics
    # ------------------------------------------------------------
    full_text_summaries_without_citations = {}

    for pmid, summary in full_text_summaries_with_citations.items():
        full_text_summaries_without_citations[pmid] = clean_summary_text(remove_citation_parentheses(summary))

    full_text_summaries = full_text_summaries_without_citations
    _ = full_text_summaries

    # ------------------------------------------------------------
    # 7. Generate abstract summaries using original method
    # ------------------------------------------------------------
    print("\nGenerating abstract summaries...")
    print("-------------------------------")

    titles_from_abstracts, abstracts = fetch_abstracts(pmids, fetch)
    _ = titles_from_abstracts

    abstract_summaries = await abstract_citation_summarize_many_article_async(
        abstracts,
        max_length=max_summary_length,
        prompt_file_path=Path(__file__).resolve().parents[2] / "full_summarizer_prompt",
        concurrency=15
    )

    for pmid, summary in abstract_summaries.items():
        abstract_summaries[pmid] = clean_summary_text(summary)

    abstract_summaries_without_citations = {}
     
    for pmid, summary in abstract_summaries.items():
        abstract_summaries_without_citations[pmid] = clean_summary_text(remove_citation_parentheses(summary))

    # ------------------------------------------------------------
    # 8. PubMed links
    # ------------------------------------------------------------
    links = {
        pmid: f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        for pmid in pmids
    }

    # ------------------------------------------------------------
    # 9. Similarity between abstract summary and full-text summary
    # ------------------------------------------------------------
    similarity_scores = {
        pmid: evaluate_similarity(
            abstract_summaries_without_citations[pmid],
            full_text_summaries_without_citations[pmid]
        )
        for pmid in abstract_summaries_without_citations
        if abstract_summaries_without_citations[pmid] != "No text available"
        and full_text_summaries_without_citations.get(pmid)
        and full_text_summaries_without_citations[pmid] != "No text available"
    }

    # ------------------------------------------------------------
    # 10. Readability scores
    # ------------------------------------------------------------
    abstract_readability = {
        pmid: compute_readability(abstract_summaries_without_citations[pmid])
        for pmid in abstract_summaries_without_citations
    }

    full_text_readability = {
        pmid: compute_readability(full_text_summaries_without_citations[pmid])
        for pmid in full_text_summaries_without_citations
    }

    # ------------------------------------------------------------
    # 11. Full text availability
    # ------------------------------------------------------------
    full_text_availability = {
        pmid: "Available" if full_texts.get(pmid) != "Full text unavailable" else "Unavailable"
        for pmid in pmids
    }

    # ------------------------------------------------------------
    # 12. RAGAS faithfulness & Summarization Score
    # ------------------------------------------------------------
    ragas_prompt = (
        "Summarize this article in 250 to 350 words for an adult lay reader "
        "with 2nd grade level scientific experience. Use simple words. "
        "The tone should be casual. "
        "Avoid emotive or negative language such as battle or fight. "
        "Keep words under 4 syllables and sentences under 10 words."
    )

    print("\nComputing RAGAS faithfulness...")
    print("------------------------------")

    abstract_ragas_faithfulness = compute_ragas_faithfulness(
        abstract_summaries_without_citations,
        abstracts,
        ragas_prompt
    )

    fulltext_ragas_faithfulness = compute_ragas_faithfulness(
        full_text_summaries_without_citations,
        full_texts,
        ragas_prompt
    )

    abstract_ragas_summarization = await compute_ragas_summarization_score(
    abstract_summaries_without_citations,
    abstracts
    )

    fulltext_ragas_summarization = await compute_ragas_summarization_score(
        full_text_summaries_without_citations,
        full_texts
    )

    ###Calculate the smog index & gunning fog score of the article summaries and store as a dict
    smog_index = {}
    gunning_fog_score = {}
    for pmid in full_text_summaries_without_citations:
        smog_index[pmid] = calculate_smog_index(full_text_summaries_without_citations[pmid])
        gunning_fog_score[pmid] = calculate_gunning_fog_score(full_text_summaries_without_citations[pmid])


    # ------------------------------------------------------------
    # 13. Prepare DataFrames
    # ------------------------------------------------------------
    titles = {
        pmid: article_metadata[pmid]["title"]
        for pmid in article_metadata
    }

    Title = pd.DataFrame(
        list(titles.items()),
        columns=["pmid", "Title"]
    )

    Link = pd.DataFrame(
        list(links.items()),
        columns=["pmid", "Link"]
    )

    Abstract = pd.DataFrame(
        list(abstracts.items()),
        columns=["pmid", "Abstract"]
    )

    Abstract = Abstract.assign(
        Abstract=lambda df: df["Abstract"].str.replace("\n", " ")
    )

    FullTextFlag = pd.DataFrame(
        list(full_text_availability.items()),
        columns=["pmid", "FullText_Availability"]
    )

    Abstract_Summary = pd.DataFrame(
        list(abstract_summaries_without_citations.items()),
        columns=["pmid", "Abstract_Summary"]
    )

    Full_Text_Summary_With_Citations = pd.DataFrame(
        list(full_text_summaries_with_citations.items()),
        columns=["pmid", "Full_Text_Summary_With_In_Text_Citations"]
    )

    Full_Text_Summary_Without_Citations = pd.DataFrame(
        list(full_text_summaries_without_citations.items()),
        columns=["pmid", "Full_Text_Summary_Without_Citations"]
    )

    # Keep original column name for compatibility.
    # This column is citation-free.
    Full_Text_Summary = pd.DataFrame(
        list(full_text_summaries_without_citations.items()),
        columns=["pmid", "Full_Text_Summary"]
    )

    Similarity = pd.DataFrame(
        list(similarity_scores.items()),
        columns=["pmid", "Abstract_vs_FullText_Similarity"]
    )

    Abstract_Readability = pd.DataFrame([
        {
            "pmid": pmid,
            "Abstract_Flesch_Reading_Ease": scores[0],
            "Abstract_Flesch_Kincaid_Grade": scores[1]
        }
        for pmid, scores in abstract_readability.items()
    ])

    Full_Text_Readability = pd.DataFrame([
        {
            "pmid": pmid,
            "FullText_Flesch_Reading_Ease": scores[0],
            "FullText_Flesch_Kincaid_Grade": scores[1]
        }
        for pmid, scores in full_text_readability.items()
    ])

    Abstract_SMOG_Index = pd.DataFrame([
        {
            "pmid": pmid,
            "Abstract_SMOG_Index": calculate_smog_index(abstract_summaries_without_citations[pmid])
        }
        for pmid in abstract_summaries_without_citations
    ])

    Full_Text_SMOG_Index = pd.DataFrame([
        {
            "pmid": pmid,
            "FullText_SMOG_Index": score
        }
        for pmid, score in smog_index.items()
    ])

    Abstract_Gunning_Fog_Score = pd.DataFrame([
        {
            "pmid": pmid,
            "Abstract_Gunning_Fog_Score": calculate_gunning_fog_score(abstract_summaries_without_citations[pmid])
        }
        for pmid in abstract_summaries_without_citations
    ])

    Full_Text_Gunning_Fog_Score = pd.DataFrame([
        {
            "pmid": pmid,
            "FullText_Gunning_Fog_Score": score
        }
        for pmid, score in gunning_fog_score.items()
    ])

    Abstract_RAGAS_Faithfulness = pd.DataFrame(
        list(abstract_ragas_faithfulness.items()),
        columns=["pmid", "Abstract_RAGAS_Faithfulness"]
    )

    FullText_RAGAS_Faithfulness = pd.DataFrame(
        list(fulltext_ragas_faithfulness.items()),
        columns=["pmid", "FullText_RAGAS_Faithfulness"]
    )

    Abstract_RAGAS_Summarization = pd.DataFrame(
        list(abstract_ragas_summarization.items()),
        columns=["pmid", "Abstract_RAGAS_Summarization_Score"]
    )

    FullText_RAGAS_Summarization = pd.DataFrame(
        list(fulltext_ragas_summarization.items()),
        columns=["pmid", "FullText_RAGAS_Summarization_Score"]
    )
    # ------------------------------------------------------------
    # 14. Citation metadata DataFrame
    # ------------------------------------------------------------
    citation_metadata_rows = []

    for pmid in citation_summary_results:
        result = citation_summary_results[pmid]

        citation_metadata_rows.append({
            "pmid": pmid,
            "Raw_Summary_With_Evidence_IDs": result["raw_summary_with_evidence_ids"],
            "Number_of_In_Text_Citations_Found": result["citation_count"],
            "Used_Evidence_IDs": ", ".join(result["used_evidence_ids"]),
            "Invalid_Evidence_IDs": ", ".join(result["invalid_evidence_ids"]),
            "Source_Evidence_Blocks_Sent_To_GPT": result["source_evidence_count"],
            "Total_Source_Paragraphs": len(citation_source_tables[pmid])
        })

    Citation_Metadata = pd.DataFrame(citation_metadata_rows)

    # ------------------------------------------------------------
    # 15. Combine all final output DataFrames
    # ------------------------------------------------------------
    data_frames = [
        Title,
        Link,
        Abstract,
        FullTextFlag,
        Abstract_Summary,
        Full_Text_Summary_With_Citations,
        Full_Text_Summary_Without_Citations,
        Full_Text_Summary,
        Citation_Metadata,
        Similarity,
        Abstract_Readability,
        Full_Text_Readability,
        Abstract_RAGAS_Faithfulness,
        FullText_RAGAS_Faithfulness,
        Abstract_RAGAS_Summarization,
        FullText_RAGAS_Summarization,
        Abstract_SMOG_Index,
        Full_Text_SMOG_Index,
        Abstract_Gunning_Fog_Score,
        Full_Text_Gunning_Fog_Score
        ]

    df_full = reduce(
        lambda left, right: pd.merge(left, right, on="pmid", how="outer"),
        data_frames
    )

    # ------------------------------------------------------------
    # 16. Print full-text availability
    # ------------------------------------------------------------
    if keyword is not None:
        keyword_for_printing = keyword
    else:
        keyword_for_printing = "PMID list"

    print(f"\nFull Text Availability for '{keyword_for_printing}':")

    availability_counts = df_full["FullText_Availability"].value_counts()

    print("Full Text Availability Counts:")
    print(availability_counts)

    # ------------------------------------------------------------
    # 17. Keep only articles with full text available
    # ------------------------------------------------------------
    df_full = df_full[df_full["FullText_Availability"] == "Available"]

    # ------------------------------------------------------------
    # 18. Save final summary CSV
    # ------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_file is not None:
        base_name, _ = os.path.splitext(output_file)
    elif "queries" in config and len(config["queries"]) > 0:
        base_name, _ = os.path.splitext(config["queries"][0]["output_file"])
    else:
        base_name = "citation_integrated_results"

    output_file_with_timestamp = f"{base_name}_with_citations_{timestamp}.csv"

    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    full_output_path = output_dir / output_file_with_timestamp

    df_full.to_csv(full_output_path, index=False, encoding="utf-8-sig")

    print("\nFinal integrated CSV saved to:")
    print(full_output_path)

    # ------------------------------------------------------------
    # 19. Save citation source table CSV
    # ------------------------------------------------------------
    combined_source_tables = []

    for pmid, source_table in citation_source_tables.items():
        if not source_table.empty:
            table_copy = source_table.copy()

            used_ids = citation_summary_results[pmid]["used_evidence_ids"]

            table_copy["used_in_summary"] = table_copy["evidence_id"].isin(used_ids)

            combined_source_tables.append(table_copy)

    citation_source_df = pd.DataFrame()
    source_table_output_path = None

    if combined_source_tables:
        citation_source_df = pd.concat(
            combined_source_tables,
            ignore_index=True
        )

        source_table_output_file = f"{base_name}_citation_source_table_{timestamp}.csv"
        source_table_output_path = output_dir / source_table_output_file

        citation_source_df.to_csv(source_table_output_path, index=False, encoding="utf-8-sig")

        print("\nCitation source table CSV saved to:")
        print(source_table_output_path)

    else:
        print("\nNo citation source table was saved because no citation evidence was found.")

    # ------------------------------------------------------------
    # 20. Display final DataFrame
    # In a .py file, we return it instead of display(df_full).
    # ------------------------------------------------------------
    print("\nFinal DataFrame preview:")
    print(df_full.head())

    return {
        "df_full": df_full,
        "citation_source_df": citation_source_df,
        "final_csv_path": full_output_path,
        "citation_source_table_path": source_table_output_path,
    }


def run_pipeline(config_path="./config.json"):
    """
    Synchronous wrapper used by run_pipeline.py.
    """
    return asyncio.run(run_pipeline_async(config_path=config_path))

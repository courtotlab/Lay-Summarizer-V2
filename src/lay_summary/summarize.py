"""
OpenAI summarization helpers.

Source of truth:
- GPT4_Code.ipynb Cell 2:
  async_summarize
  gpt4_summarize_async

Minimal change:
- async_client is set by set_async_client() from run_pipeline.py.
"""

import asyncio
from lay_summary.citations import (
    citation_count_readable_citations,
    citation_count_words_without_citations,
    citation_make_evidence_blocks_for_prompt,
    citation_convert_evidence_ids_to_readable_citations,
    split_sentences,
    abstract_assign_sentence_labels,
    abstract_build_evidence_table,
    abstract_make_gpt_readable_text
)
import pandas as pd
from openai import AsyncOpenAI


async_client = None


def set_async_client(openai_api_key):
  
    #Create the AsyncOpenAI client.
    global async_client
    async_client = AsyncOpenAI(api_key=openai_api_key) # create the AsyncOpenAI client and set it to the global variable, later for summarizer


def load_summarizer_prompt(text, max_length, prompt_file_path):
    
    with open(prompt_file_path, "r", encoding="utf-8") as file:
        prompt_template = file.read()

    complete_prompt = prompt_template.format(
        max_length=max_length,
        evidence_text=text
    )

    return complete_prompt


async def abstract_citation_summarize_one_article_async(pmid, text, max_length, prompt_file_path):
    # Summarize one text.

    if async_client is None:
        raise ValueError("async_client is not set. Call set_async_client(openai_api_key) first.")

    if not text or text == "Abstract unavailable":
        return pmid, "No text available"
    

    sentences = split_sentences(text)
    labeled_sentences = abstract_assign_sentence_labels(sentences)
    evidence_table = abstract_build_evidence_table(labeled_sentences)
    evidence_text = abstract_make_gpt_readable_text(labeled_sentences)


    prompt = load_summarizer_prompt(text=evidence_text, 
                                    max_length=max_length, 
                                    prompt_file_path=prompt_file_path
                                    )


    try:
        response = await async_client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": (
                    "You are a careful biomedical summarizer. "
                    "You write accurate biomedical lay summaries at about a 7th to 8th grade reading level with sparse, non-crowded citations."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        print(f"Abstract summarizer model used: {response.model}")

        raw_summary = response.choices[0].message.content.strip()

    except Exception as e:
        return pmid, f"Error summarizing: {e}"
    
    readable_summary, _, _ = citation_convert_evidence_ids_to_readable_citations(raw_summary, evidence_table)

    return pmid, readable_summary


async def abstract_citation_summarize_many_article_async(texts, max_length,  prompt_file_path, concurrency=15):

    #Summarize many abstracts asynchronously.

    semaphore = asyncio.Semaphore(concurrency)

    async def limited_summary(pmid, text):
        async with semaphore:
            return await abstract_citation_summarize_one_article_async(pmid, text, max_length, prompt_file_path)
            
    tasks = [limited_summary(pmid, text) for pmid, text in texts.items()]
    results = await asyncio.gather(*tasks)

    return dict(results)


async def citation_summarize_one_article_async(
    pmid,
    title,
    source_table,
    max_length,
    prompt_file_path,
    model_name="gpt-5.1"
):
    
    # Citation-aware summarizer with stricter citation-density rules.

    if async_client is None:
        raise ValueError("async_client is not set. Call set_async_client(openai_api_key) first.")

    if source_table is None or source_table.empty:
        return {
            "pmid": pmid,
            "raw_summary_with_evidence_ids": "No source evidence available.",
            "summary_with_readable_citations": "No source evidence available.",
            "used_evidence_ids": [],
            "invalid_evidence_ids": [],
            "citation_count": 0,
            "word_count": 0,
            "selected_evidence_count": 0,
        }

    evidence_text = citation_make_evidence_blocks_for_prompt(source_table)

    prompt = load_summarizer_prompt(
        text=evidence_text,
        max_length=max_length,
        prompt_file_path=prompt_file_path
    )

    try:
        response = await async_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful biomedical summarizer. "
                        "You write accurate biomedical lay summaries at about a 7th to 8th grade reading level with sparse, non-crowded citations."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2
        )
        print(f"Citation summarizer model used: {response.model}")
        raw_summary = response.choices[0].message.content.strip()

    except Exception as error:
        raw_summary = f"Error summarizing PMID {pmid}: {error}"

    readable_summary, used_ids, invalid_ids = citation_convert_evidence_ids_to_readable_citations(
        raw_summary,
        source_table
    )

    citation_count = citation_count_readable_citations(readable_summary)
    word_count = citation_count_words_without_citations(readable_summary)

    return {
        "pmid": pmid,
        "raw_summary_with_evidence_ids": raw_summary,
        "summary_with_readable_citations": readable_summary,
        "used_evidence_ids": used_ids,
        "invalid_evidence_ids": invalid_ids,
        "citation_count": citation_count,
        "word_count": word_count,
        "source_evidence_count": len(source_table),
    }


async def citation_summarize_many_articles_async(
    article_metadata,
    source_tables,
    max_length,
    prompt_file_path,
    concurrency=5,
    model_name="gpt-5.1"
):
    
    # Generate citation-aware summaries for all PMIDs.

    semaphore = asyncio.Semaphore(concurrency)

    async def limited_summary(pmid):
        async with semaphore:
            metadata = article_metadata.get(pmid, {})
            title = metadata.get("title", "Title unavailable")
            source_table = source_tables.get(pmid, pd.DataFrame())

            result = await citation_summarize_one_article_async(
                pmid=pmid,
                title=title,
                source_table=source_table,
                max_length=max_length,
                prompt_file_path=prompt_file_path,
                model_name=model_name
            )

            return pmid, result

    tasks = []

    for pmid in article_metadata:
        tasks.append(limited_summary(pmid))

    results = await asyncio.gather(*tasks)

    summary_results = {}

    for pmid, result in results:
        summary_results[pmid] = result

    return summary_results

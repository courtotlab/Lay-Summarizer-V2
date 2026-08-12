"""
Metric and cleanup helpers.
"""

import re
from ragas.llms import llm_factory
from ragas.metrics.collections import SummaryScore
from openai import AsyncOpenAI
import textstat
from datasets import Dataset
from langchain_openai import ChatOpenAI
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import faithfulness
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_summary_text(summary):
    """
    Clean summary text before saving it or scoring it.

    This does NOT remove parentheses, brackets, citations, or abbreviations.
    It only fixes formatting problems such as:
        organs.Many -> organs. Many
        cells.In contrast -> cells. In contrast

    It also normalizes extra spaces, tabs, and newlines.
    """
    if summary is None:
        return ""

    summary = str(summary)

    # Replace non-breaking spaces with regular spaces.
    summary = summary.replace("\u00a0", " ")

    # Add a missing space after sentence-ending punctuation
    # when the next character starts a new sentence.
    summary = re.sub(r"(?<=[.!?])(?=[A-Z])", " ", summary)

    # Normalize extra spaces, tabs, and newlines.
    summary = re.sub(r"\s+", " ", summary)

    # Remove accidental spaces before punctuation.
    summary = re.sub(r"\s+([.,;:!?])", r"\1", summary)

    return summary.strip()


def remove_full_text_citation_parentheses(summary):
  
    if summary is None:
        return ""

    summary = str(summary)

    summary_without_citations = re.sub(
        r"\s*\([^)]*para\.\s*\d+[^)]*\)",
        "",
        summary
    )

    summary_without_citations = re.sub(r"\s+", " ", summary_without_citations)

    summary_without_citations = re.sub(
        r"\s+([.,;:!?])",
        r"\1",
        summary_without_citations
    )

    return summary_without_citations.strip()


def remove_abstract_citation_parentheses(summary):

    if summary is None:
        return ""

    summary = str(summary)

    summary_without_citations = re.sub(
        r"\s*\([^)]*Abstract,\s*sentence\s*\d+[^)]*\)",
        "",
        summary
    )

    summary_without_citations = re.sub(r"\s+", " ", summary_without_citations)

    summary_without_citations = re.sub(
        r"\s+([.,;:!?])",
        r"\1",
        summary_without_citations
    )

    return summary_without_citations.strip()


def evaluate_similarity(abstract_summary, full_text_summary):
    """
    Calculate TF-IDF cosine similarity.

    """
    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(
        [abstract_summary, full_text_summary]
    )

    similarity = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:2]
    )

    return similarity[0][0]


def compute_readability(summary):
    """
    Compute Flesch Reading Ease and Flesch-Kincaid Grade.

    Copied from the notebook.
    """
    if summary and summary != "No text available":
        summary = clean_summary_text(summary)
        flesch_score = textstat.flesch_reading_ease(summary)
        grade_level = textstat.flesch_kincaid_grade(summary)
        return flesch_score, grade_level

    else:
        return None, None


def compute_ragas_faithfulness(summaries,
                               references, 
                               prompt, 
                               model="gpt-5.1"):
    """
    Compute RAGAS faithfulness.

    Copied closely from the notebook, with one small safety check:
    if there are no valid PMIDs, return an empty dictionary.
    """
    print(f"RAGAS faithfulness model used for evaluation: {model}")

    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=model))

    data = {
        "question": [],
        "answer": [],
        "contexts": []
    }

    valid_pmids = []

    for pmid, summary in summaries.items():
        reference = references.get(pmid)

        if (
            summary
            and reference
            and summary != "No text available"
            and reference != "Full text unavailable"
        ):
            data["question"].append(prompt)
            data["answer"].append(summary)
            data["contexts"].append([reference])
            valid_pmids.append(pmid)

    if not valid_pmids:
        return {}

    dataset = Dataset.from_dict(data)
    results = evaluate(dataset, metrics=[faithfulness], llm=evaluator_llm)

    return dict(zip(valid_pmids, results["faithfulness"]))


async def compute_ragas_summarization_score(response,
                                           references,
                                           model="gpt-5.1"):
                                        #    max_reference_chars=30000):

    client = AsyncOpenAI()
    llm = llm_factory(model, client=client)
    scorer = SummaryScore(llm=llm)
    scores = {}

    for pmid, summary in response.items():
        reference = references.get(pmid)

        if (
            summary
            and reference
            and summary != "No text available"
            and reference != "Full text unavailable"
            and reference != "Abstract unavailable"
        ):
            # Truncate very long references to avoid hitting the model's output
            # token limit during keyphrase extraction.

            try:
                result = await scorer.ascore(
                    reference_contexts=[reference],
                    response=summary
                )
                scores[pmid] = result.value
            except Exception as e:
                print(f"  Warning: RAGAS summarization score failed for PMID {pmid}: {e}")
                scores[pmid] = None

    return scores


def calculate_smog_index(summary):

    if summary and summary != "No text available":
        summary = clean_summary_text(summary)
        return textstat.smog_index(summary)
    else:
        return None
    

def calculate_gunning_fog_score(summary):
    if summary and summary != "No text available":
        summary = clean_summary_text(summary)
        return textstat.gunning_fog(summary)
    else:
        return None
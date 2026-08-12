
from src.lay_summary.config import load_project_config, setup_pubmed_fetcher
from src.lay_summary.fetch import fetch_full_texts
from src.lay_summary.metrics import compute_ragas_summarization_score


PMID = "34650974"

SUMMARY = """Breast cancer is very common and can be deadly, especially when it has spread in the body. Researchers studied over 1,000 breast tumors to see how certain gene changes link to patient survival. They grouped the tumors into two gene types and compared stages of cancer and patient deaths. One group had more advanced cancers and more deaths, showing a clearly worse outlook over time. This group also had fewer gene changes of a certain kind, called mutation burden, than the better-outcome group. Researchers then looked at 130 genes that differed between the two groups and picked 11 linked to survival. They built a risk score using these 11 genes and split patients into high and low risk groups. People in the high risk group died more often, and the score predicted 1, 3, and 5 year survival well. The score also worked in a second group of 50 breast cancer patients from another database. A chart that combines this gene score with basic clinical facts may help doctors estimate a person’s outlook. If confirmed in more patients, this kind of gene-based risk tool could guide follow-up and treatment choices."""


async def main():
    # Build the fetcher (same as the pipeline does).
    config = load_project_config("./config.json")
    fetch = setup_pubmed_fetcher(config)

    # Force your summary in; let the helper fetch the full text.
    full_text_summaries_without_citations = {PMID: SUMMARY}
    _, full_texts = fetch_full_texts([PMID], fetch)

    if full_texts.get(PMID) == "Full text unavailable":
        raise ValueError(f"No full text available for PMID {PMID}.")

    # Score.
    fulltext_ragas_summarization = await compute_ragas_summarization_score(
        full_text_summaries_without_citations,
        full_texts
    )

    print(f"\nPMID {PMID}")
    print(f"FullText RAGAS Summarization Score: {fulltext_ragas_summarization[PMID]}")


if __name__ == "__main__":
    asyncio.run(main())
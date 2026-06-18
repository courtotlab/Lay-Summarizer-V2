"""
Citation/evidence workflow helpers.

Source of truth:
- GPT4_Code.ipynb Cell 7: base citation helper cell
- GPT4_Code.ipynb Cell 8: patch cell that reduces crowded citations

Important:
- The patch cell redefines several functions from the base helper cell.
- This file keeps the final patched behavior, because that is the behavior
  used by the integrated main summarization cell.
"""

import re
import time

import pandas as pd
from Bio import Entrez
from bs4 import BeautifulSoup


def citation_clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"\s+", " ", text) #replace multiple white spaces into one

    return text.strip()


def citation_normalize_section_title(section_title):
    if section_title is None:
        return "Body"

    title = citation_clean_text(section_title).lower()
    title = re.sub(r"^\d+(\.\d+)*\.?\s*", "", title) #strip off leading number liek 3.1

    if title == "":
        return "Body"

    if "abstract" in title:
        return "Abstract"

    if "intro" in title or "background" in title:
        return "Introduction"

    if (
        "method" in title
        or "materials" in title
        or "patient" in title
        or "study design" in title
        or "experimental" in title
    ):
        return "Methods"

    if "result" in title or "finding" in title:
        return "Results"

    if "discussion" in title:
        return "Discussion"

    if "conclusion" in title or "summary" in title:
        return "Conclusion"

    return "Body"


def citation_find_section_for_paragraph(paragraph_tag):
    # find the most suitable section titles where the paragraph(tag) is located within the XML structure, and return both:
    # - display_raw: the innermost section title as written in the XML (shown to users)
    # - best_normalized: the nearest recognized canonical name (used for quota/priority)

    # for paragraphs in a nested strcutre, find a list of sec tag from the innermost to outermost.
    section_tags = paragraph_tag.find_parents("sec") #
    first_raw_title = None
    best_normalized = "Body"

    for sec in section_tags:
        title_tag = sec.find("title", recursive=False) #find the title tag of this paragraph

        if title_tag is None:
            continue

        raw_title = citation_clean_text(title_tag.get_text(" ", strip=True))

        if first_raw_title is None:
            first_raw_title = raw_title

        if best_normalized == "Body":
            best_normalized = citation_normalize_section_title(raw_title) # match with given dict of stardardized section, if matched, then use that section title to conclude the section of the input paragraph.
    
    if first_raw_title:
        display_raw = first_raw_title
    else:
        display_raw = "Body"

    return best_normalized, display_raw


def citation_extract_evidence_table_for_one_pmid(pmid, fetcher):
    #Extract PMC XML paragraphs and turn them into citation evidence rows in teh evidence block.

    time.sleep(1)

    article = fetcher.article_by_pmid(pmid)
    if article.title:
        title = article.title
    else:
        title = "Title unavailable"
    pmcid = article.pmc

    columns = [
        "pmid",
        "pmcid",
        "evidence_id",
        "section",
        "paragraph_number",
        "citation_label",
        "text",
    ]

    if not pmcid:
        return title, None, pd.DataFrame(columns=columns)

    pmcid_text = str(pmcid)
    pmcid_for_entrez = pmcid_text.replace("PMC", "").strip()

    handle = Entrez.efetch(
        db="pmc",
        id=pmcid_for_entrez,
        rettype="xml",
        retmode="xml"
    )

    xml_data = handle.read()
    handle.close()

    soup = BeautifulSoup(xml_data, features="xml")

    rows = []
    section_counts = {}
    evidence_number = 1

    def add_row(section, paragraph_text):
        #add a row to the evidence table for citation, each row is one paragraph with its unique info
        nonlocal evidence_number

        text = citation_clean_text(paragraph_text)

        if len(text) < 40:
            return

        section_counts[section] = section_counts.get(section, 0) + 1
        paragraph_number = section_counts[section]

        evidence_id = f"E{evidence_number}"
        citation_label = f"{section.title()}, para. {paragraph_number}"

        rows.append({
            "pmid": str(pmid),
            "pmcid": pmcid_text,
            "evidence_id": evidence_id,
            "section": section,
            "paragraph_number": paragraph_number,
            "citation_label": citation_label,
            "text": text,
        })

        evidence_number += 1

    abstract_tag = soup.find("abstract")

    if abstract_tag is not None:
        abstract_paragraphs = abstract_tag.find_all("p")

        if abstract_paragraphs:
            for paragraph in abstract_paragraphs:
                add_row("Abstract", paragraph.get_text(" ", strip=True))
        else:
            add_row("Abstract", abstract_tag.get_text(" ", strip=True))

    body_tag = soup.find("body")

    if body_tag is not None:
        body_paragraphs = body_tag.find_all("p")
    else:
        body_paragraphs = soup.find_all("p")

    # skip paragraphs that are within figure/table/caption/ref etc, or 
    # within abstract (because they are already extracted as evidence from the abstract section), 
    # and only keep those in the main body text that are not within those sections.
    skip_parent_names = [
        "table-wrap",
        "fig",
        "caption",
        "ref-list",
        "ref",
        "fn-group",
        "app-group",
    ]

    for paragraph in body_paragraphs:
        if paragraph.find_parent("abstract") is not None:
            continue

        should_skip = False

        for parent_name in skip_parent_names:
            if paragraph.find_parent(parent_name) is not None:
                should_skip = True
                break

        if should_skip:
            continue

        section, _ = citation_find_section_for_paragraph(paragraph)
        text = paragraph.get_text(" ", strip=True)

        add_row(section, text)

    source_table = pd.DataFrame(rows, columns=columns)

    return title, pmcid_text, source_table


def citation_choose_rows_for_prompt(source_table, max_rows=45):
    """
    Choose a manageable number of evidence paragraphs for GPT.

    Copied from the notebook.
    """
    if source_table is None or source_table.empty:
        return pd.DataFrame()

    if len(source_table) <= max_rows:
        return source_table.copy()

    selected_parts = []

    section_quotas = {
        "Abstract": 2,
        "Introduction": 5,
        "Methods": 6,
        "Results": 12,
        "Discussion": 7,
        "Conclusion": 4,
        "Body": 18,
    }

    for section, quota in section_quotas.items(): #keep only the row that has the section selected
        section_rows = source_table[source_table["section"] == section]

        if not section_rows.empty: # Keep only certain number of row according to the quotas
            selected_parts.append(section_rows.head(quota))

    if selected_parts:
        selected_table = pd.concat(selected_parts)
    else:
        selected_table = source_table.head(max_rows) # cut off the rows to reinforce the max_rows limit (rows are cut from the tail)

    selected_table = selected_table.drop_duplicates(subset=["evidence_id"])
    selected_table = selected_table.head(max_rows)

    return selected_table.copy()


def citation_make_evidence_blocks_for_prompt(source_table, max_chars_per_block=900):
    #Convert evidence rows into GPT-readable evidence blocks.

    if source_table is None or source_table.empty:
        return "No evidence blocks available."

    blocks = []

    for _, row in source_table.iterrows():
        text = citation_clean_text(row["text"])

        if len(text) > max_chars_per_block:
            text = text[:max_chars_per_block].rstrip() + "..."

        block = (
            f"[{row['evidence_id']}]\n"
            f"Section: {row['section']}\n"
            f"Paragraph: {row['paragraph_number']}\n"
            f"Text: {text}"
        )

        blocks.append(block)

    return "\n\n".join(blocks)


def citation_choose_best_evidence_id(evidence_ids, source_table):

    #Patched version from the notebook patch cell.

    #If GPT gives multiple evidence IDs for one idea, choose ONE best ID.
    
    if not evidence_ids:
        return None

    if source_table is None or source_table.empty:
        return evidence_ids[0]

    evidence_to_section = {}

    for _, row in source_table.iterrows():
        evidence_to_section[row["evidence_id"]] = row["section"]

    section_priority = {
        "Results": 1,
        "Conclusion": 2,
        "Methods": 3,
        "Discussion": 4,
        "Introduction": 5,
        "Body": 6,
        "Abstract": 9,
    }

    best_id = evidence_ids[0]
    best_score = 999

    for evidence_id in evidence_ids:
        section = evidence_to_section.get(evidence_id, "Body")
        score = section_priority.get(section, 8)

        if score < best_score: # override the best_id if this evidence_id is from a more important section
            best_score = score
            best_id = evidence_id

    return best_id


def citation_collapse_adjacent_readable_citations(text):
    #Collapse citations like: (Abstract, para. 1)(Introduction, para. 4)
    #into one citation --> (Abstract, para. 1)

    if text is None:
        return ""

    text = str(text)

    #match any text with strucutre like [intro, para.1][intro, para.2] (adjacent readable citations)
    adjacent_pattern = r"(\([^)]*para\.\s*\d+[^)]*\))(?:\s*(\([^)]*para\.\s*\d+[^)]*\)))+"

    def choose_one_readable_citation(match):
        citation_cluster = match.group(0)
        citations = re.findall(r"\([^)]*para\.\s*\d+[^)]*\)", citation_cluster)

        if not citations:
            return citation_cluster

        non_abstract_citations = []

        for citation in citations:
            if "Abstract" not in citation:
                non_abstract_citations.append(citation)

        if non_abstract_citations:
            return non_abstract_citations[-1]

        return citations[-1]

    previous_text = None

    while previous_text != text:
        previous_text = text
        text = re.sub(adjacent_pattern, choose_one_readable_citation, text)

    return text


def citation_convert_evidence_ids_to_readable_citations(summary_text, source_table):
    """
    Patched version from the notebook patch cell.

    Convert GPT's internal evidence IDs into readable citations:
    - [E4] becomes (Results, para. 2)
    - [E4, E5] becomes only ONE best citation
    - [E4][E5] becomes only ONE best citation
    - [E4] [E5] becomes only ONE best citation
    """
    if summary_text is None:
        return "", [], []

    if source_table is None or source_table.empty:
        return str(summary_text), [], []

    evidence_to_label = {}

    for _, row in source_table.iterrows():
        evidence_to_label[row["evidence_id"]] = row["citation_label"]

    used_ids = []
    invalid_ids = []

    #match any text with structure like [E4, E5] or [E4][E5] (clusters of evidence ids)
    citation_cluster_pattern = r"(?:\[(?:\s*E\d+\s*,?\s*)+\]\s*)+"

    def replace_cluster(match): # helper function to replace eg[E4, E5] or [E4][E5] into one best readable citation
        cluster_text = match.group(0)
        evidence_ids = re.findall(r"E\d+", cluster_text) # make cluster ids into a list of elements

        if not evidence_ids:
            return ""

        for evidence_id in evidence_ids:
            used_ids.append(evidence_id)

            if evidence_id not in evidence_to_label:
                invalid_ids.append(evidence_id)

        valid_ids = []

        for evidence_id in evidence_ids:
            if evidence_id in evidence_to_label:
                valid_ids.append(evidence_id)

        if not valid_ids:
            return ""

        best_id = citation_choose_best_evidence_id(valid_ids, source_table)
        best_label = evidence_to_label[best_id]

        return f"({best_label})"

    readable_summary = re.sub(citation_cluster_pattern, replace_cluster, str(summary_text)) # replace all cluster citation into best single citation

    readable_summary = re.sub(r"\s+([.,;:])", r"\1", readable_summary)#replace all cluster citation into best single citation
    readable_summary = re.sub(r"\s+", " ", readable_summary).strip() #replace multiple white spaces into one and trim
    readable_summary = citation_collapse_adjacent_readable_citations(readable_summary) #collapse adjacent citations into one citation

    used_ids_unique = []

    for evidence_id in used_ids:
        if evidence_id not in used_ids_unique:
            used_ids_unique.append(evidence_id)

    invalid_ids_unique = []

    for evidence_id in invalid_ids:
        if evidence_id not in invalid_ids_unique:
            invalid_ids_unique.append(evidence_id)

    return readable_summary, used_ids_unique, invalid_ids_unique


def citation_count_readable_citations(summary_text):
    if summary_text is None:
        return 0

    citations = re.findall(
        r"\([^)]*para\.\s*\d+[^)]*\)",
        str(summary_text)
    )

    return len(citations)


def citation_count_words_without_citations(summary_text):
    if summary_text is None:
        return 0

    text = str(summary_text)
    text = re.sub(r"\s*\([^)]*para\.\s*\d+[^)]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if text == "":
        return 0

    return len(text.split())

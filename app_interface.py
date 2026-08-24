import html as html_module
import json
import re
import sys
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from urllib.parse import quote
import streamlit.components.v1 as components

# ------------------------------------------------------------
# 1. Make sure Streamlit can import your backend from src/
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_FOLDER = PROJECT_ROOT / "src"

if str(SRC_FOLDER) not in sys.path:
    sys.path.insert(0, str(SRC_FOLDER))


from lay_summary.pipeline import run_pipeline  # noqa: E402

DEFAULT_ENTREZ_EMAIL = "osborn.s.xs07@gmail.com"
DEFAULT_ENTREZ_API_KEY = "0140f08c57e308d5a8191207044ef199d008"


def source_url_for(pmid, pmcid):
    """PMC article page if the article is in PMC, else the PubMed abstract page."""
    pmcid = str(pmcid or "").strip()
    if pmcid:
        if not pmcid.upper().startswith("PMC"):
            pmcid = "PMC" + pmcid
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
 
    pmid = str(pmid or "").strip()
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
 
 
def render_summary_with_hover_citations(summary_text, source_df, base_url, text_column="text"):
    if not summary_text:
        return ""
    if not base_url or source_df is None or source_df.empty:
        return html_module.escape(summary_text)
 
    label_to_text = {
        str(row["citation_label"]).strip(): row[text_column]
        for _, row in source_df.iterrows()
        if str(row.get("citation_label", "")).strip()
    }
 
    def build_link(label, evidence_text):
        preview = normalize_text_for_text_fragment(evidence_text)[:200].rstrip()
        tooltip = html_module.escape(f"{label.strip()} \u2014 {preview}", quote=True)
        target_url = html_module.escape(
            build_text_fragment_url(base_url, evidence_text), quote=True
        )
        return (
            f'<a href="{target_url}" target="_blank" rel="noopener" title="{tooltip}" '
            f'style="color:#0077CC;text-decoration:none;border-bottom:1px dotted #0077CC;">'
            f'({html_module.escape(label)})</a>'
        )
 
    # Split on any (...) group: even indices are plain text, odd are the inner label.
    parts = re.split(r"\(([^()]*)\)", summary_text)
    return "".join(
        html_module.escape(part) if i % 2 == 0
        else (build_link(part, label_to_text[part.strip()])
              if part.strip() in label_to_text
              else html_module.escape(f"({part})"))
        for i, part in enumerate(parts)
    )

def render_full_text_summary_html(rendered_html, plain_text=""):
    """Render the citation-linked summary in an iframe component instead of
    st.markdown, so rel="noopener" survives and the text-fragment highlight
    activates (the component iframe allows popups to escape the sandbox)."""
    approx_chars = len(plain_text) if plain_text else len(rendered_html)
    height = min(1400, max(200, int(approx_chars * 0.55) + 80))

    document = f"""
        <div style="
            font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', Roboto, sans-serif;
            font-size: 1rem;
            line-height: 1.6;
            color: #262730;
        ">{rendered_html}</div>
    """
    components.html(document, height=height, scrolling=True)


def normalize_text_for_text_fragment(text):
    """
    Prepare evidence paragraph text for a browser Text Fragment URL.
 
    Text Fragments are sensitive to whitespace and exact rendered text, so this
    collapses repeated whitespace before building #:~:text= links.
    """
    if text is None:
        return ""
 
    text = str(text).replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def encode_text_directive_component(text):
    """Percent-encode text for a #:~:text= directive. '-' is a structural
    delimiter in the grammar, so force-encode it (quote() leaves it alone)."""
    return quote(text, safe="").replace("-", "%2D")


def _clean_anchor(text):
    """Trim edge punctuation that often differs between the extracted text and
    the rendered HTML (curly quotes, dashes, brackets)."""
    return text.strip(" \t\"'\u201c\u201d\u2018\u2019.,;:!?\u2014\u2013-()[]{}")


def _first_clean_word(word):
    """Return the word only if it's safe for an anchor: plain ASCII letters
    (with - or '). Words with digits/non-ASCII are likely reference
    superscripts or typographic chars that won't match the page."""
    if not word:
        return None
    if any(not (c.isascii() and (c.isalpha() or c in "-'")) for c in word):
        return None
    return word


def build_text_fragment_url(base_url, evidence_text, max_words=20):
    """Build a PMC URL with a single short #:~:text= anchor from the first few
    plain words of the paragraph, stopped before the first risky word."""
    if not base_url:
        return ""

    text = normalize_text_for_text_fragment(evidence_text)
    if not text:
        return base_url

    base = str(base_url).split("#", 1)[0]

    safe_words = []
    for word in text.split(" "):
        clean_word = _first_clean_word(word)
        if clean_word is None:
            break
        safe_words.append(clean_word)
        if len(safe_words) >= max_words:
            break

    anchor = _clean_anchor(" ".join(safe_words))

    # Too-generic one/two-word anchor -> fall back to a plain slice.
    if len(anchor.split()) < 3:
        anchor = _clean_anchor(" ".join(text.split(" ")[:max_words]))
    if not anchor:
        return base

    return f"{base}#:~:text={encode_text_directive_component(anchor)}"

# ------------------------------------------------------------
# 2. Page setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="Lay Summary Generator",
    layout="wide"
)

st.title("Biomedical Lay Summary Generator")

st.write(
    "Fetch PubMed articles, generate plain-language summaries with citations, "
    "compute readability metrics, and export results as CSV."
)


# ------------------------------------------------------------
# 3. Input mode selector
# ------------------------------------------------------------
st.subheader("Input mode")

input_mode = st.radio(
    "How would you like to provide articles?",
    options=["Search PubMed by keyword", "Enter PubMed IDs manually", "Upload papers in PDF format"],
    horizontal=True
)


# ------------------------------------------------------------
# 4. Pipeline settings form
# ------------------------------------------------------------
st.subheader("Pipeline settings")

with st.form("pipeline_form"):

    # --- Mode-specific inputs ---
    if input_mode == "Search PubMed by keyword":
        keyword = st.text_input("PubMed keyword", value="renal cancer")
        num_of_articles = st.number_input(
            "Number of articles",
            min_value=1,
            max_value=20,
            value=1,
            step=1
        )
        pmid_text = ""
    elif input_mode == "Enter PubMed IDs manually":
        st.write("Paste one PubMed ID per line:")
        pmid_text = st.text_area("PubMed IDs", height=150, placeholder="38390862\n39012345\n...")
        keyword = ""
        num_of_articles = None
    else:
        st.write("Upload PDF files:")
        pdf_files = st.file_uploader("Choose PDF files", accept_multiple_files=False, type=["pdf"],)
        keyword = ""
        num_of_articles = None

    # --- Shared settings ---
    col1, col2 = st.columns(2)

    with col1:
        min_summary_length = st.number_input(
            "Minimum summary length (words)",
            min_value=50,
            max_value=500,
            value=250,
            step=10
        )

    with col2:
        max_summary_length = st.number_input(
            "Maximum summary length (words)",
            min_value=100,
            max_value=1000,
            value=350,
            step=10
        )

    entrez_email = st.text_input("Entrez email", value=DEFAULT_ENTREZ_EMAIL)
    entrez_api_key = st.text_input("Entrez API key", value=DEFAULT_ENTREZ_API_KEY, type="password")

    submitted = st.form_submit_button("Run summarizer")


# ------------------------------------------------------------
# 5. Validation and run
# ------------------------------------------------------------
if submitted:
    errors = []

    if entrez_email.strip() == "":
        errors.append("Please enter your Entrez email.")

    if entrez_api_key.strip() == "":
        errors.append("Please enter your Entrez API key.")

    if min_summary_length > max_summary_length:
        errors.append("Minimum summary length cannot be greater than maximum.")

    if input_mode == "Search PubMed by keyword" and keyword.strip() == "":
        errors.append("Please enter a PubMed keyword.")

    if input_mode == "Upload papers in PDF format":
        if not pdf_files:
            errors.append("Please upload at least one PDF file.")

    pmids_entered = []
    if input_mode == "Enter PubMed IDs manually":
        pmids_entered = [line.strip() for line in pmid_text.splitlines() if line.strip()]
        if not pmids_entered:
            errors.append("Please enter at least one PubMed ID.")

    for error in errors:
        st.error(error)

    if not errors:

        # --- Build temporary config ---
        temporary_config = {
            "entrez_email": entrez_email,
            "entrez_api_key": entrez_api_key,
            "max_summary_length": int(max_summary_length),
            "min_summary_length": int(min_summary_length),
            "output_directory": "./output",
        }

        pmid_tmp_path = None
        pdf_temp_path = []
        if input_mode == "Search PubMed by keyword":
            temporary_config["num_of_articles"] = int(num_of_articles)
            temporary_config["queries"] = [
                {
                    "keyword": keyword.strip(),
                    "output_file": keyword.strip().replace(" ", "_") + ".csv"
                }
            ]
            # No pmid_file key → pipeline runs a fresh keyword search
        elif input_mode == "Upload papers in PDF format":
            temp_pdf = tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=PROJECT_ROOT,
            delete=False,
            prefix="uploaded_paper_")

            temp_pdf.write(pdf_files.read())
            temp_pdf.close()
            pdf_temp_path.append(str(temp_pdf.name))

            temporary_config["num_of_articles"] = len(pdf_temp_path)
            temporary_config["pdf_files"] = pdf_temp_path

        else:
            # Write user-supplied PMIDs to a temp file; pipeline reads via pmid_file
            pmid_tmp = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                dir=PROJECT_ROOT,
                delete=False,
                prefix="user_pmids_"
            )
            for pmid in pmids_entered:
                pmid_tmp.write(pmid + "\n")
            pmid_tmp.close()
            pmid_tmp_path = Path(pmid_tmp.name)

            temporary_config["num_of_articles"] = len(pmids_entered)
            temporary_config["pmid_file"] = str(pmid_tmp_path)
            # No queries key → pipeline goes straight to pmid_file

        config_path = PROJECT_ROOT / "streamlit_config.json"

        with open(config_path, "w") as config_file:
            json.dump(temporary_config, config_file, indent=4)

        # --- Run ---
        with st.spinner("Running the pipeline..."):
            try:
                result = run_pipeline(config_path=str(config_path))

                df_full = result["df_full"]
                citation_source_df = result.get("citation_source_df", pd.DataFrame())
                abstract_source_df = result.get("abstract_source_df", pd.DataFrame())
                final_csv_path = result["final_csv_path"]
                citation_source_table_path = result.get("citation_source_table_path")
                abstract_source_table_path = result.get("abstract_source_table_path")

                st.success("Pipeline finished.")

                st.subheader("Summary results")
                st.dataframe(df_full, use_container_width=True)

                st.subheader("Download")

                with open(final_csv_path, "rb") as file:
                    st.download_button(
                        label="Download summary CSV",
                        data=file,
                        file_name=Path(final_csv_path).name,
                        mime="text/csv"
                    )

                if citation_source_table_path is not None:
                    with open(citation_source_table_path, "rb") as file:
                        st.download_button(
                            label="Download full-text citation source table CSV",
                            data=file,
                            file_name=Path(citation_source_table_path).name,
                            mime="text/csv"
                        )

                if abstract_source_table_path is not None:
                    with open(abstract_source_table_path, "rb") as file:
                        st.download_button(
                            label="Download abstract sentence evidence table CSV",
                            data=file,
                            file_name=Path(abstract_source_table_path).name,
                            mime="text/csv"
                        )

                if not citation_source_df.empty:
                    st.subheader("Full-text citation source table")
                    st.dataframe(citation_source_df, use_container_width=True)

                st.subheader("Abstract sentence evidence table")
                if not abstract_source_df.empty:
                    st.dataframe(abstract_source_df, use_container_width=True)
                else:
                    st.info("No abstract sentence evidence table was returned by the pipeline.")

                # --- Per-article summaries with abstract + full-text evidence ---
                st.subheader("Per-article summaries")

                pmid_to_pmcid = {}
                if not citation_source_df.empty:
                    for _, row in citation_source_df.iterrows():
                        pmid_to_pmcid[str(row["pmid"])] = str(row.get("pmcid", ""))

                for _, article_row in df_full.iterrows():
                    pmid = str(article_row.get("pmid", ""))
                    title = article_row.get("Title", pmid)
                    pmcid = pmid_to_pmcid.get(pmid, "")

                    abstract_summary = article_row.get(
                        "Abstract_Summary_With_In_Text_Citations",
                        article_row.get("Abstract_Summary", "")
                    )
                    full_text_summary = article_row.get("Full_Text_Summary_With_In_Text_Citations", "")

                    if not citation_source_df.empty:
                        article_citations = citation_source_df[
                            citation_source_df["pmid"].astype(str) == pmid
                        ]
                    else:
                        article_citations = citation_source_df

                    if not abstract_source_df.empty:
                        article_abstract_evidence = abstract_source_df[
                            abstract_source_df["pmid"].astype(str) == pmid
                        ]
                    else:
                        article_abstract_evidence = abstract_source_df

                    with st.expander(f"{title} (PMID: {pmid})", expanded=False):
                        abstract_tab, full_text_tab, evidence_tab = st.tabs([
                            "Abstract summary",
                            "Full-text summary",
                            "Evidence tables"
                        ])

                        with abstract_tab:
                            st.markdown("#### Abstract summary")
                            if abstract_summary:
                                rendered = render_summary_with_hover_citations(
                                    abstract_summary, article_abstract_evidence,
                                    source_url_for(pmid, pmcid), text_column="sentence"
                                )
                                render_full_text_summary_html(rendered, abstract_summary)
                            else:
                                st.write("No abstract summary available for this article.")

                        with full_text_tab:
                            st.markdown("#### Full-text summary")
                            if full_text_summary:
                                rendered = render_summary_with_hover_citations(
                                    full_text_summary, article_citations,
                                    source_url_for(pmid, pmcid), text_column="text"
                                )
                                render_full_text_summary_html(
                                    rendered, full_text_summary
                                )
                            else:
                                st.write("No full-text summary available for this article.")

                        with evidence_tab:
                            st.markdown("#### Abstract sentence evidence")
                            if not article_abstract_evidence.empty:
                                st.dataframe(article_abstract_evidence, use_container_width=True)
                            else:
                                st.info("No abstract sentence evidence rows for this article.")

                            st.markdown("#### Full-text citation evidence")
                            if not article_citations.empty:
                                st.dataframe(article_citations, use_container_width=True)
                            else:
                                st.info("No full-text citation evidence rows for this article.")


                # FREEZE PIPELINE OUTPUT FOR THE STATIC SITE 
                # Paste this INSIDE the `try:` block, at 16-space indentation,
                # AFTER the per-article `for` loop ends and BEFORE `except Exception`.
                # =====================================================================
                freeze_dir = Path(temporary_config["output_directory"]) / "frozen_results"
                freeze_dir.mkdir(parents=True, exist_ok=True)

                # Columns in df_full that are text/identifiers, NOT readability metrics.
                NON_METRIC_COLS = {
                    "pmid", "pmcid", "Title",
                    "Abstract", "Full_Text",
                    "Abstract_Summary",
                    "Abstract_Summary_With_In_Text_Citations",
                    "Full_Text_Summary",
                    "Full_Text_Summary_With_In_Text_Citations",
                }

                def _to_records(df):
                    """DataFrame -> list of plain dicts (NaN -> None, numpy -> native)."""
                    if df is None or df.empty:
                        return []
                    return json.loads(df.to_json(orient="records"))

                def _label_map(df, text_column):
                    """{citation_label: evidence_text} — mirrors render_summary_with_hover_citations."""
                    out = {}
                    if df is None or df.empty:
                        return out
                    if "citation_label" not in df.columns or text_column not in df.columns:
                        return out
                    for _, row in df.iterrows():
                        label = str(row.get("citation_label", "")).strip()
                        if label:
                            out[label] = str(row.get(text_column, "") or "")
                    return out

                frozen_count = 0
                for _, article_row in df_full.iterrows():
                    pmid = str(article_row.get("pmid", "")).strip()
                    if not pmid:
                        continue

                    title = str(article_row.get("Title", pmid))
                    pmcid = pmid_to_pmcid.get(pmid, "")

                    # Same per-article slicing the UI already does
                    if not citation_source_df.empty:
                        art_citations = citation_source_df[
                            citation_source_df["pmid"].astype(str) == pmid
                        ]
                    else:
                        art_citations = citation_source_df

                    if not abstract_source_df.empty:
                        art_abstract_ev = abstract_source_df[
                            abstract_source_df["pmid"].astype(str) == pmid
                        ]
                    else:
                        art_abstract_ev = abstract_source_df

                    # Readability metrics: numeric columns only, so text columns
                    # (journal, authors, abstract...) never leak into the metrics panel.
                    metrics = {}
                    for key, value in article_row.items():
                        if key in NON_METRIC_COLS:
                            continue
                        try:
                            if pd.isna(value):
                                continue
                        except (TypeError, ValueError):
                            continue
                        if isinstance(value, bool):
                            continue
                        if isinstance(value, (int, float)) or hasattr(value, "dtype"):
                            try:
                                metrics[str(key)] = float(value)
                            except (TypeError, ValueError):
                                pass

                    frozen_payload = {
                        "id": pmid,
                        "title": title,
                        "pmid": pmid,
                        "pmcid": pmcid,
                        # Resolved here so the static builder never has to guess:
                        # PMC page if available, else the PubMed abstract page.
                        "source_url": source_url_for(pmid, pmcid),

                        "abstract_summary": article_row.get(
                            "Abstract_Summary_With_In_Text_Citations",
                            article_row.get("Abstract_Summary", "")
                        ) or "",
                        "full_text_summary": article_row.get(
                            "Full_Text_Summary_With_In_Text_Citations", ""
                        ) or "",

                        # Label -> evidence text. Note the different text columns:
                        # abstract evidence uses "sentence", full-text uses "text".
                        "abstract_citations": _label_map(art_abstract_ev, "sentence"),
                        "full_text_citations": _label_map(art_citations, "text"),

                        # Raw rows, kept for the CSV download button on the static page.
                        "abstract_evidence_rows": _to_records(art_abstract_ev),
                        "citation_evidence_rows": _to_records(art_citations),

                        "metrics": metrics,
                    }

                    with open(freeze_dir / f"{pmid}.json", "w", encoding="utf-8") as json_file:
                        json.dump(frozen_payload, json_file, indent=2, ensure_ascii=False, default=str)
                    frozen_count += 1

                st.success(
                    f"Froze {frozen_count} article(s) to `{freeze_dir}`. "
                    "Now run `python build_static_site.py` to build the shareable pages."
                )
                # =====================================================================






            except Exception as error:
                st.error("The pipeline failed.")
                st.exception(error)

            finally:
                # Clean up the temp PMID file if one was created
                if pmid_tmp_path is not None:
                    pmid_tmp_path.unlink(missing_ok=True)

                for pdf_path in pdf_temp_path:
                    Path(pdf_path).unlink(missing_ok=True)
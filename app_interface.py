import html as html_module
import json
import re
import sys
import tempfile
from pathlib import Path
import streamlit as st


# ------------------------------------------------------------
# 1. Make sure Streamlit can import your backend from src/
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_FOLDER = PROJECT_ROOT / "src"

if str(SRC_FOLDER) not in sys.path:
    sys.path.insert(0, str(SRC_FOLDER))


from lay_summary.pipeline import run_pipeline  # noqa: E402


def render_summary_with_hover_citations(summary_text, citation_source_df, pmcid):
    """
    Replace each (Section, para. N) citation in the summary with an HTML link.

    Hovering shows the evidence paragraph text as a browser tooltip.
    Clicking opens the PMC article in a new tab.

    If pmcid is empty (article not in PMC), citations are left as plain text.
    """
    if not summary_text:
        return ""

    if not pmcid or citation_source_df is None or citation_source_df.empty:
        return html_module.escape(summary_text)

    # Build a lookup from citation_label to the evidence paragraph text.
    label_to_text = {}
    for _, row in citation_source_df.iterrows():
        label = row.get("citation_label", "")
        text = row.get("text", "")
        if label:
            label_to_text[label] = text

    pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"

    # Match any (... para. N ...) citation pattern.
    citation_pattern = r"\(([^)]*para\.\s*\d+[^)]*)\)"

    def replace_citation(match):
        label = match.group(1)          # e.g. "3.2 Primary Outcomes, para. 2"
        evidence_text = label_to_text.get(label, "")

        if not evidence_text:
            return match.group(0)       # no match found, leave as plain text

        preview = evidence_text[:200].rstrip()
        if len(evidence_text) > 200:
            preview += "..."

        tooltip = html_module.escape(f"{label} — {preview}", quote=True)

        return (
            f'<a href="{pmc_url}" target="_blank" '
            f'title="{tooltip}" '
            f'style="color:#0077CC;text-decoration:none;border-bottom:1px dotted #0077CC;">'
            f'({label})</a>'
        )

    # Escape the summary text first, then re-insert citation HTML.
    # We escape the non-citation parts by splitting around citations.
    parts = re.split(citation_pattern, summary_text)
    output_parts = []

    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Even indices are plain text between citations — escape for HTML.
            output_parts.append(html_module.escape(part))
        else:
            # Odd indices are the captured citation label text.
            # Reconstruct the full match to pass through replace_citation.
            full_match_text = f"({part})"
            output_parts.append(re.sub(citation_pattern, replace_citation, full_match_text))

    return "".join(output_parts)


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

    entrez_email = st.text_input("Entrez email", value="")
    entrez_api_key = st.text_input("Entrez API key", value="", type="password")

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
                citation_source_df = result["citation_source_df"]
                final_csv_path = result["final_csv_path"]
                citation_source_table_path = result["citation_source_table_path"]

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
                            label="Download citation source table CSV",
                            data=file,
                            file_name=Path(citation_source_table_path).name,
                            mime="text/csv"
                        )

                if not citation_source_df.empty:
                    st.subheader("Citation source table")
                    st.dataframe(citation_source_df, use_container_width=True)

                # --- Per-article summaries with hoverable citations ---
                st.subheader("Summaries")

                # Build a lookup from pmid to pmcid using the citation source table.
                pmid_to_pmcid = {}
                if not citation_source_df.empty:
                    for _, row in citation_source_df.iterrows():
                        pmid_to_pmcid[str(row["pmid"])] = str(row.get("pmcid", ""))

                for _, article_row in df_full.iterrows():
                    pmid = str(article_row.get("pmid", ""))
                    title = article_row.get("Title", pmid)
                    summary = article_row.get("Full_Text_Summary_With_In_Text_Citations", "")
                    pmcid = pmid_to_pmcid.get(pmid, "")

                    # Filter citation_source_df to rows for this article only.
                    if not citation_source_df.empty:
                        article_citations = citation_source_df[
                            citation_source_df["pmid"].astype(str) == pmid
                        ]
                    else:
                        article_citations = citation_source_df

                    with st.expander(f"{title} (PMID: {pmid})", expanded=False):
                        if summary:
                            rendered = render_summary_with_hover_citations(
                                summary, article_citations, pmcid
                            )
                            st.markdown(rendered, unsafe_allow_html=True)
                        else:
                            st.write("No full-text summary available for this article.")

            except Exception as error:
                st.error("The pipeline failed.")
                st.exception(error)

            finally:
                # Clean up the temp PMID file if one was created
                if pmid_tmp_path is not None:
                    pmid_tmp_path.unlink(missing_ok=True)

                for pdf_path in pdf_temp_path:
                    Path(pdf_path).unlink(missing_ok=True)
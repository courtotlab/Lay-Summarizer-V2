"""
build_static_site.py

Reads the frozen pipeline output written by app_interface.py
(output/frozen_results/*.json) and builds a self-contained static site:

    output/site/
        index.html
        article-<pmid>.html
        data/<pmid>-abstract-evidence.csv
        data/<pmid>-citation-evidence.csv

No server, no Streamlit. Open index.html in a browser or drop the
folder on GitHub Pages / Netlify.

Run:  python build_static_site.py
"""

import csv
import html as html_module
import json
import re
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parent
FROZEN_DIR = PROJECT_ROOT / "output" / "frozen_results"
SITE_DIR = PROJECT_ROOT / "output" / "site"
DATA_DIR = SITE_DIR / "data"


# ------------------------------------------------------------------
# Text-fragment helpers — ported verbatim in behaviour from the app so
# the static pages link into PMC exactly the way the Streamlit UI did.
# ------------------------------------------------------------------
def normalize_text_for_text_fragment(text):
    if text is None:
        return ""
    text = str(text).replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).strip()


def encode_text_directive_component(text):
    return quote(text, safe="").replace("-", "%2D")


def _clean_anchor(text):
    return text.strip(" \t\"'\u201c\u201d\u2018\u2019.,;:!?\u2014\u2013-()[]{}")


def _first_clean_word(word):
    if not word:
        return None
    if any(not (c.isascii() and (c.isalpha() or c in "-'")) for c in word):
        return None
    return word


def build_text_fragment_url(base_url, evidence_text, boundary_words=5):
    """Builds a URL text fragment using a RANGE strategy (start,end).
    
    This instructs the browser to highlight everything starting from the first
    few words all the way to the last few words of the evidence text.
    """
    if not base_url:
        return ""
    text = normalize_text_for_text_fragment(evidence_text)
    if not text:
        return base_url

    base = str(base_url).split("#", 1)[0]
    words = text.split(" ")

    # For short text, use simple exact string matching
    if len(words) <= boundary_words * 2:
        anchor = _clean_anchor(" ".join(words))
        if not anchor:
            return base
        return f"{base}#:~:text={encode_text_directive_component(anchor)}"

    # For longer text, use Range strategy: start_phrase,end_phrase
    start_anchor = _clean_anchor(" ".join(words[:boundary_words]))
    end_anchor = _clean_anchor(" ".join(words[-boundary_words:]))

    if not start_anchor or not end_anchor:
        return base

    start_encoded = encode_text_directive_component(start_anchor)
    end_encoded = encode_text_directive_component(end_anchor)

    return f"{base}#:~:text={start_encoded},{end_encoded}"


def render_summary_with_hover_citations(summary_text, label_to_text, base_url):
    """Turn '(Label)' markers into hover-titled links into the source article.

    label_to_text is the {citation_label: evidence_text} dict already baked
    into the frozen JSON, so nothing has to be recomputed here.
    """
    if not summary_text:
        return ""
    if not base_url or not label_to_text:
        return html_module.escape(summary_text)

    def build_link(label, evidence_text):
        preview = normalize_text_for_text_fragment(evidence_text)[:200].rstrip()
        tooltip = html_module.escape(f"{label.strip()} \u2014 {preview}", quote=True)
        target = html_module.escape(
            build_text_fragment_url(base_url, evidence_text), quote=True
        )
        return (
            f'<a class="cite" href="{target}" target="_blank" rel="noopener" '
            f'title="{tooltip}">({html_module.escape(label)})</a>'
        )

    parts = re.split(r"\(([^()]*)\)", summary_text)
    return "".join(
        html_module.escape(part) if i % 2 == 0
        else (
            build_link(part, label_to_text[part.strip()])
            if part.strip() in label_to_text
            else html_module.escape(f"({part})")
        )
        for i, part in enumerate(parts)
    )


# ------------------------------------------------------------------
# Small HTML builders
# ------------------------------------------------------------------
def rows_to_table(rows, empty_message):
    if not rows:
        return f'<p class="empty">{html_module.escape(empty_message)}</p>'

    columns = list(rows[0].keys())
    head = "".join(f"<th>{html_module.escape(str(c))}</th>" for c in columns)

    body = []
    for row in rows:
        cells = "".join(
            f"<td>{html_module.escape('' if row.get(c) is None else str(row.get(c)))}</td>"
            for c in columns
        )
        body.append(f"<tr>{cells}</tr>")

    return (
        '<div class="table-scroll"><table>'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div>"
    )


def rows_to_csv(rows, path):
    if not rows:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in columns})
    return path


def metrics_to_html(metrics):
    if not metrics:
        return '<p class="empty">No readability metrics were recorded.</p>'
    items = []
    for key, value in metrics.items():
        label = html_module.escape(str(key).replace("_", " "))
        items.append(
            f'<div class="metric"><span class="metric-value">{value:.2f}</span>'
            f'<span class="metric-label">{label}</span></div>'
        )
    return f'<div class="metrics">{"".join(items)}</div>'


CSS = """
:root {
  --ink: #1b1f24;
  --muted: #5c6673;
  --line: #dfe3e8;
  --bg: #fbfbfa;
  --panel: #ffffff;
  --accent: #1f6f8b;
  --accent-soft: #eaf2f5;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.6;
}
.wrap { max-width: 62rem; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }
a { color: var(--accent); }
h1 { font-size: 1.8rem; line-height: 1.25; margin: 0 0 .5rem; }
h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.eyebrow {
  font-size: .75rem; letter-spacing: .09em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 .75rem;
}
.meta {
  color: var(--muted); font-size: .9rem; margin: 0 0 2rem;
  display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
}
.btn-source {
  display: inline-block;
  background-color: var(--accent);
  color: #ffffff !important;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 0.4rem 0.85rem;
  border-radius: 4px;
  text-decoration: none;
  transition: background-color 0.2s ease;
}
.btn-source:hover {
  background-color: #154c60;
  text-decoration: none;
}

/* Tabs — CSS only. No JavaScript, so these keep working inside sandboxed
   iframes, under strict CSP, and with scripts disabled entirely. */
.tabset { position: relative; }
.tabset > input[type="radio"] {
  position: absolute; opacity: 0; width: 1px; height: 1px;
  /* kept in the DOM and focusable so keyboard users can tab/arrow through */
}
.tabs { display: flex; gap: .25rem; border-bottom: 1px solid var(--line); }
.tab {
  cursor: pointer; font-size: .95rem; color: var(--muted);
  padding: .7rem 1rem; border-bottom: 2px solid transparent;
  margin-bottom: -1px; user-select: none; white-space: nowrap;
}
.tab:hover { color: var(--ink); }

.panel {
  display: none;
  background: var(--panel);
  border: 1px solid var(--line);
  border-top: 0;
  padding: 1.5rem;
}

/* Selected states: sibling combinators from the checked radio. */
#t-abstract:checked ~ .tabs label[for="t-abstract"],
#t-fulltext:checked ~ .tabs label[for="t-fulltext"],
#t-evidence:checked ~ .tabs label[for="t-evidence"] {
  color: var(--accent); border-bottom-color: var(--accent); font-weight: 600;
}
#t-abstract:checked ~ #p-abstract,
#t-fulltext:checked ~ #p-fulltext,
#t-evidence:checked ~ #p-evidence { display: block; }

/* Visible keyboard focus, since the real input is off-screen. */
#t-abstract:focus-visible ~ .tabs label[for="t-abstract"],
#t-fulltext:focus-visible ~ .tabs label[for="t-fulltext"],
#t-evidence:focus-visible ~ .tabs label[for="t-evidence"] {
  outline: 2px solid var(--accent); outline-offset: 2px;
}

.summary { font-size: 1.02rem; }
a.cite {
  color: var(--accent); text-decoration: none;
  border-bottom: 1px dotted var(--accent);
}
a.cite:hover { background: var(--accent-soft); }

.empty { color: var(--muted); font-style: italic; }
.table-scroll { overflow-x: auto; margin-bottom: 1.5rem; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; }
th, td {
  border: 1px solid var(--line); padding: .45rem .6rem;
  text-align: left; vertical-align: top;
}
th { background: var(--accent-soft); font-weight: 600; white-space: nowrap; }
td { max-width: 32rem; }

.metrics { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.75rem; }
.metric {
  border: 1px solid var(--line); background: var(--panel);
  padding: .7rem 1rem; min-width: 8rem;
}
.metric-value { display: block; font-size: 1.3rem; font-weight: 600; }
.metric-label { display: block; font-size: .75rem; color: var(--muted); text-transform: capitalize; }

.downloads { margin-top: 1rem; font-size: .9rem; }
.card {
  display: block; background: var(--panel); border: 1px solid var(--line);
  padding: 1rem 1.25rem; margin-bottom: .75rem; text-decoration: none; color: inherit;
}
.card:hover { border-color: var(--accent); }
.card-title { font-weight: 600; margin-bottom: .2rem; }
.card-meta { color: var(--muted); font-size: .85rem; }
h3 { font-size: .95rem; margin: 1.5rem 0 .6rem; }
h3:first-child { margin-top: 0; }
@media (max-width: 40rem) { .tab { padding: .6rem .7rem; font-size: .85rem; } }
"""

def build_article_page(article):
    pmid = article.get("pmid") or article.get("id") or ""
    title = article.get("title") or pmid
    source_url = article.get("source_url") or ""

    abstract_summary = article.get("abstract_summary") or ""
    full_text_summary = article.get("full_text_summary") or ""

    abstract_html = render_summary_with_hover_citations(
        abstract_summary, article.get("abstract_citations") or {}, source_url
    ) or '<p class="empty">No abstract summary available for this article.</p>'

    full_text_html = render_summary_with_hover_citations(
        full_text_summary, article.get("full_text_citations") or {}, source_url
    ) or '<p class="empty">No full-text summary available for this article.</p>'

    abstract_rows = article.get("abstract_evidence_rows") or []
    citation_rows = article.get("citation_evidence_rows") or []

    abstract_csv = rows_to_csv(abstract_rows, DATA_DIR / f"{pmid}-abstract-evidence.csv")
    citation_csv = rows_to_csv(citation_rows, DATA_DIR / f"{pmid}-citation-evidence.csv")

    downloads = []
    if abstract_csv:
        downloads.append(f'<a href="data/{abstract_csv.name}" download>Download abstract evidence (CSV)</a>')
    if citation_csv:
        downloads.append(f'<a href="data/{citation_csv.name}" download>Download citation evidence (CSV)</a>')
    downloads_html = (
        f'<p class="downloads">{" &middot; ".join(downloads)}</p>' if downloads else ""
    )

    source_link = (
        f'<a href="{html_module.escape(source_url)}" class="btn-source" target="_blank" rel="noopener">View source article &rarr;</a>'
        if source_url else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_module.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow"><a href="index.html">&larr; All summaries</a></p>
  <h1>{html_module.escape(title)}</h1>
  <p class="meta"><span>PMID {html_module.escape(str(pmid))}</span> {source_link}</p>
  
  <div class="tabset">
    <input type="radio" name="tabs" id="t-abstract" checked>
    <input type="radio" name="tabs" id="t-fulltext">
    <input type="radio" name="tabs" id="t-evidence">

    <div class="tabs">
      <label class="tab" for="t-abstract">Abstract summary</label>
      <label class="tab" for="t-fulltext">Full-text summary</label>
      <label class="tab" for="t-evidence">Evidence tables</label>
    </div>

    <section class="panel" id="p-abstract">
      <div class="summary">{abstract_html}</div>
    </section>

    <section class="panel" id="p-fulltext">
      <div class="summary">{full_text_html}</div>
    </section>

    <section class="panel" id="p-evidence">
      <h3>Abstract sentence evidence</h3>
      {rows_to_table(abstract_rows, "No abstract sentence evidence rows for this article.")}
      <h3>Full-text citation evidence</h3>
      {rows_to_table(citation_rows, "No full-text citation evidence rows for this article.")}
      {downloads_html}
    </section>
  </div>
  <br><br>{metrics_to_html(article.get("metrics") or {})}
</div>
</body>
</html>
"""


def build_index(articles):
    cards = []
    for article in articles:
        pmid = article.get("pmid") or article.get("id") or ""
        title = article.get("title") or pmid
        has_abstract = "Abstract summary" if article.get("abstract_summary") else None
        has_full = "Full-text summary" if article.get("full_text_summary") else None
        available = " &middot; ".join(x for x in (has_abstract, has_full) if x) or "No summaries"
        cards.append(
            f'<a class="card" href="article-{html_module.escape(str(pmid))}.html">'
            f'<div class="card-title">{html_module.escape(title)}</div>'
            f'<div class="card-meta">PMID {html_module.escape(str(pmid))} &middot; {available}</div>'
            f"</a>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lay summaries</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">Biomedical lay summary generator</p>
  <h1>Plain-language summaries</h1>
  <p class="meta">{len(articles)} article(s), frozen from the pipeline.</p>
  {"".join(cards) if cards else '<p class="empty">No frozen articles found.</p>'}
</div>
</body>
</html>
"""


def main():
    if not FROZEN_DIR.exists():
        raise SystemExit(f"No frozen results at {FROZEN_DIR}. Run the app and submit a job first.")

    json_files = sorted(FROZEN_DIR.glob("*.json"))
    if not json_files:
        raise SystemExit(f"{FROZEN_DIR} contains no .json files.")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    articles = []
    for json_file in json_files:
        with open(json_file, encoding="utf-8") as handle:
            article = json.load(handle)
        articles.append(article)

        pmid = article.get("pmid") or article.get("id") or json_file.stem
        page = build_article_page(article)
        (SITE_DIR / f"article-{pmid}.html").write_text(page, encoding="utf-8")

        abstract_len = len(article.get("abstract_summary") or "")
        full_len = len(article.get("full_text_summary") or "")
        print(f"  {pmid}: abstract {abstract_len} chars, full text {full_len} chars")

    (SITE_DIR / "index.html").write_text(build_index(articles), encoding="utf-8")
    print(f"\nBuilt {len(articles)} page(s) -> {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
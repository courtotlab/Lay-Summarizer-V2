from spacy.lang.en import English
import pandas as pd

def split_sentences(text):
    nlp = English()
    nlp.add_pipe("sentencizer")
    lst = []

    doc = nlp(text)
    for sentence in doc.sents:
        lst.append(sentence.text.strip())
    return lst


def abstract_assign_sentence_labels(sentences_list):
    labeled_sentences = []
    for i, sentence in enumerate(sentences_list, start=1):
        evidence_id = f"E{i}"
        labeled_sentences.append((evidence_id, sentence))
    return labeled_sentences



def abstract_make_gpt_readable_text(labeled_sentences):
    
    all_blocks = []

    for id, sentence in labeled_sentences:
        gpt_readable_block = f"[{id}]\nText: {sentence}"
        all_blocks.append(gpt_readable_block)
    
    evidence_text = "\n\n".join(all_blocks)
    return evidence_text


def abstract_build_evidence_table(labeled_sentences):
    rows = []

    for i, (id, sentence) in enumerate(labeled_sentences, start=1):
        citation_label = f"Abstract, sentence {i}"
        rows.append({"evidence_id": id,
                     "sentence number": i,
                     "citation_label": citation_label,
                     "sentence": sentence})
    
    
    return pd.DataFrame(rows)
        




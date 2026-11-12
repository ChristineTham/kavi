"""Streamlit interface: paste Pāḷi or Sanskrit (Markdown or plain text), get a literal English translation, the
word-by-word table and the review log.  Run with ``kavi app`` or ``streamlit run src/kavi/app.py``."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kavi.config import Settings  # noqa: E402
from kavi.dpd import DPD, analyse_text, analysis_table, special_words  # noqa: E402
from kavi.language import set_language  # noqa: E402

st.set_page_config(page_title="Kavi — Pāḷi and Sanskrit to English", page_icon="📜", layout="wide")


@st.cache_resource(show_spinner="Opening the dictionaries …")
def get_dpd(lang: str, db: str, decon_db: str, decon_json: str, data_dir: str):
    if lang == "sa":
        from kavi.sanskrit import SanskritLexicon
        return SanskritLexicon(Path(data_dir))
    return DPD(Path(db), Path(decon_db), Path(decon_json))


@st.cache_resource(show_spinner="Loading models (first time takes a minute) …")
def get_pool(translate_model: str, review_model: str):
    from kavi.models import ModelPool
    return ModelPool(translate_model, review_model, log=lambda m: None)


@st.cache_data(ttl=15, show_spinner=False)
def current_problems(lang: str, translate_model: str, review_model: str, data_dir: str) -> list[str]:
    """What is missing, asked of the disk and the model server at most every few seconds, not on every rerun."""
    s = Settings()
    s.use_language(lang)
    return s.check()


settings = Settings()

with st.sidebar:
    st.title("📜 Kavi")
    st.caption("Literal Pāḷi or Sanskrit → English. Dictionary word analysis, a discourse draft grounded word by word, and review. Runs locally, on Ollama or MLX.")
    language = st.radio("Language", ["Pāḷi", "Sanskrit (and Buddhist Hybrid Sanskrit)"], horizontal=False)
    lang = "sa" if language.startswith("Sanskrit") else "pi"
    settings.use_language(lang)
    rounds = st.slider("Review rounds", 0, 5, settings.max_rounds, help="0 = translate only")
    batch_words = st.slider("Review batch size (words)", 100, 1200, settings.eval_batch_words, step=50)
    thinking = st.checkbox("Let the reviewer think (slower)", value=settings.thinking)
    use_cache = st.checkbox("Use translation cache", value=True)
    glossary_text = st.text_area("Glossary (term: gloss per line)", value="", height=80,
                                 help="Terms to keep in the source language with a gloss, e.g. `sandhi: junction`")
    with st.expander("Models and data"):
        translate_model = st.text_input("Translate model", settings.translate_model)
        review_model = st.text_input("Review model", settings.eval_model)
        st.text(f"vidyut + Cologne: {settings.sanskrit_db}" if lang == "sa" else f"DPD: {settings.dpd_db}")
        problems = current_problems(lang, settings.translate_model, settings.eval_model, str(settings.data_dir))
        if problems:
            for p in problems:
                st.warning(p)

st.header("Sanskrit text" if lang == "sa" else "Pāḷi text")
uploaded = st.file_uploader("Upload a Markdown or text file", type=["md", "mdx", "txt"])
default_text = uploaded.read().decode("utf-8") if uploaded else ""
text = st.text_area("or paste it here", value=default_text, height=220,
                    placeholder="evaṃ mayā śrutam ekasmin samaye bhagavān śrāvastyāṃ viharati sma …" if lang == "sa"
                    else "Ekaṃ samayaṃ bhagavā bārāṇasiyaṃ viharati isipatane migadāye. …")

col1, col2 = st.columns([1, 1])
do_analyse = col1.button("Analyse words only", use_container_width=True)
do_translate = col2.button("Translate", type="primary", use_container_width=True)

if (do_analyse or do_translate) and text.strip():
    dpd = get_dpd(lang, str(settings.dpd_db), str(settings.decon_db), str(settings.decon_json), str(settings.data_dir))
    set_language(dpd)                                  # the analysis reads the language record as the translation does
    if do_analyse:
        analyses = analyse_text(dpd, text)
        st.subheader("Word analysis (vidyut and the Cologne dictionaries)" if lang == "sa" else "Word analysis (Digital Pāḷi Dictionary)")
        st.markdown(analysis_table(analyses))
        sp = special_words(analyses)
        for kind, items in sp.items():
            if items:
                st.caption(f"{kind}: " + ", ".join(f"{w} → {g}" for w, g in items))
        missing = [a.surface for a in analyses if not a.found]
        if missing:
            st.info("Not in the dictionaries: " + ", ".join(missing))
    else:
        from kavi.pipeline import Translator

        s = Settings()
        s.use_language(lang)
        s.max_rounds, s.eval_batch_words, s.thinking = rounds, batch_words, thinking
        s.translate_model, s.eval_model = translate_model, review_model
        if glossary_text.strip():
            gpath = Path(s.cache_dir) / "streamlit-glossary.txt"
            gpath.parent.mkdir(parents=True, exist_ok=True)
            gpath.write_text(glossary_text, encoding="utf-8")
            s.glossary = gpath
        pool = get_pool(translate_model, review_model)
        log = st.empty()
        messages: list[str] = []

        def progress(msg: str):
            messages.append(msg)
            log.code("\n".join(messages[-8:]), language=None)

        with st.spinner("Translating …"):
            tr = Translator(s, dpd, pool, progress=progress, use_cache=use_cache)
            result = tr.translate_markdown(text, review=rounds > 0)
        log.empty()
        st.success(f"{len(result.units)} segments · {result.model_calls} model calls · {result.seconds:.0f}s")
        tab1, tab2, tab3, tab4 = st.tabs(["Translation", "Side by side", "Word analysis", "Review log"])
        with tab1:
            st.markdown(result.markdown)
            st.download_button("Download translation (.md)", result.markdown, file_name="translation.md")
        with tab2:
            for u in result.units:
                a, b = st.columns(2)
                a.markdown(u.source)
                b.markdown(u.final)
                st.divider()
        with tab3:
            st.markdown(result.table())
            st.download_button("Download table (.md)", result.table(), file_name="word-analysis.md")
        with tab4:
            st.markdown(result.report())
elif do_translate or do_analyse:
    st.warning("Paste or upload some Sanskrit first." if lang == "sa" else "Paste or upload some Pāḷi first.")

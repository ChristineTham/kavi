"""Command line interface.

    kavi translate text.md -o text.en.md        # translate a Markdown or plain-text file
    kavi translate --text "Namo tassa …"         # translate a string
    echo "…" | kavi translate                    # or stdin
    kavi analyse "Ekaṃ samayaṃ bhagavā …"        # the DPD word-by-word table only
    kavi setup                                   # download and convert both MITRA models to MLX
    kavi doctor                                  # check data files and models
    kavi app                                     # the Streamlit interface
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import IT_HF, IT_MLX, MODELS_DIR, TRANSLATE_HF, TRANSLATE_MLX, Settings


def _settings(args) -> Settings:
    s = Settings()
    if getattr(args, "data_dir", None):
        s.data_dir = Path(args.data_dir).expanduser()
    if getattr(args, "translate_model", None):
        s.translate_model = args.translate_model
    if getattr(args, "review_model", None):
        s.eval_model = args.review_model
    if getattr(args, "rounds", None) is not None:
        s.max_rounds = args.rounds
    if getattr(args, "no_review", False):
        s.max_rounds = 0
    if getattr(args, "think", False):
        s.thinking = True
    if getattr(args, "max_tokens", None):
        s.max_tokens = args.max_tokens
    if getattr(args, "sentence_words", None):
        s.sentence_words = args.sentence_words
    if getattr(args, "batch_words", None):
        s.eval_batch_words = args.batch_words
    if getattr(args, "glossary", None):
        s.glossary = None if args.glossary.lower() == "none" else Path(args.glossary).expanduser()
    return s


def _dpd(s: Settings):
    from .dpd import DPD
    return DPD(s.dpd_db, s.decon_db, s.decon_json)


def _read_input(args) -> tuple[str, str | None]:
    """(text, source name)."""
    if args.text:
        return args.text, None
    if args.paths:
        p = Path(args.paths[0])
        return p.read_text(encoding="utf-8"), str(p)
    if not sys.stdin.isatty():
        return sys.stdin.read(), None
    sys.exit("nothing to translate: give a file, --text, or pipe text on stdin")


# --------------------------------------------------------------------------------------


def cmd_translate(args) -> int:
    from .models import ModelPool
    from .pipeline import Translator

    s = _settings(args)
    problems = s.check()
    if problems:
        for p in problems:
            sys.stderr.write(f"! {p}\n")
        if any("dpd.db" in p or "model" in p for p in problems):
            return 1
    dpd = _dpd(s)
    pool = ModelPool(s.translate_model, s.eval_model)
    tr = Translator(s, dpd, pool, use_cache=not args.no_cache)
    inputs: list[tuple[str, str | None]] = []
    if args.paths and len(args.paths) > 1 or (args.paths and Path(args.paths[0]).is_dir()):
        files = []
        for raw in args.paths:
            p = Path(raw)
            files.extend(sorted(p.rglob("*.md")) + sorted(p.rglob("*.txt")) if p.is_dir() else [p])
        inputs = [(f.read_text(encoding="utf-8"), str(f)) for f in files]
    else:
        inputs = [_read_input(args)]
    for text, name in inputs:
        if name:
            sys.stderr.write(f"== {name}\n")
        result = tr.translate_markdown(text, review=s.max_rounds > 0)
        if args.out:
            out = Path(args.out)
            if out.is_dir() or (len(inputs) > 1):
                out.mkdir(parents=True, exist_ok=True)
                out = out / (Path(name).stem + ".en" + Path(name).suffix if name else "translation.md")
            out.write_text(result.markdown, encoding="utf-8")
            sys.stderr.write(f"   -> {out}\n")
        else:
            print(result.markdown)
        if args.table:
            Path(args.table).write_text(result.table(), encoding="utf-8")
            sys.stderr.write(f"   word analysis -> {args.table}\n")
        if args.report:
            Path(args.report).write_text(result.report(), encoding="utf-8")
            sys.stderr.write(f"   review report -> {args.report}\n")
        sys.stderr.write(f"   {len(result.units)} segments, {result.model_calls} model calls, {result.seconds:.0f}s\n")
    return 0


def cmd_analyse(args) -> int:
    from .dpd import analyse_text, analysis_table, reference_pairs, special_words

    s = _settings(args)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else " ".join(args.words)
    if not text.strip() and not sys.stdin.isatty():
        text = sys.stdin.read()
    dpd = _dpd(s)
    analyses = analyse_text(dpd, text)
    if args.json:
        print(json.dumps([_analysis_json(a) for a in analyses], ensure_ascii=False, indent=1))
    elif args.pairs:
        for src, gloss in reference_pairs(analyses):
            print(f"{src} Means in English: {gloss}")
    else:
        print(analysis_table(analyses, max_hw=6 if args.full else 3))
        sp = special_words(analyses)
        notes = [f"{k}: " + ", ".join(f"{w} ({g})" if g != w else w for w, g in v) for k, v in sp.items() if v]
        if notes:
            print("\n" + "\n".join(notes))
    missing = [a.surface for a in analyses if not a.found]
    sys.stderr.write(f"{len(analyses)} distinct words, {len(missing)} not in DPD" + (": " + ", ".join(missing) if missing else "") + "\n")
    return 0


def _analysis_json(a) -> dict:
    return {
        "word": a.surface, "key": a.key, "found": a.found,
        "headwords": [{"lemma": h.lemma, "pos": h.pos, "analysis": h.analysis, "meaning": h.gloss, "kind": h.kind}
                      for h in a.headwords],
        "splits": [{"parts": s.parts, "source": s.source,
                    "glosses": [[{"lemma": h.lemma, "analysis": h.analysis, "meaning": h.gloss} for h in p.headwords[:2]]
                                for p in s.analyses]} for s in a.splits],
    }


def cmd_setup(args) -> int:
    """Download both MITRA checkpoints and convert them to MLX (the checkpoints declare model_type
    qwen3_5_text, which mlx-lm does not know; it is patched to qwen3_5)."""
    from huggingface_hub import snapshot_download

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    if not args.review_only:
        jobs.append((TRANSLATE_HF, MODELS_DIR / "mitra-src", MODELS_DIR / TRANSLATE_MLX))
    if not args.translate_only:
        jobs.append((IT_HF, MODELS_DIR / "mitra-it-src", MODELS_DIR / IT_MLX))
    for repo, src, dest in jobs:
        if args.bits:
            dest = dest.with_name(dest.name.replace("bf16", f"{args.bits}bit"))
        if dest.exists() and not args.force:
            print(f"{dest} exists, skipping (use --force to rebuild)")
            continue
        print(f"downloading {repo} -> {src}")
        snapshot_download(repo, local_dir=str(src), max_workers=8)
        cfg = src / "config.json"
        c = json.loads(cfg.read_text())
        if c.get("model_type") == "qwen3_5_text":
            c["model_type"] = "qwen3_5"
            cfg.write_text(json.dumps(c, indent=2))
            print("  patched model_type -> qwen3_5")
        cmd = [sys.executable, "-m", "mlx_lm", "convert", "--hf-path", str(src), "--mlx-path", str(dest)]
        if args.bits:
            cmd += ["-q", "--q-bits", str(args.bits), "--q-group-size", "64"]
        else:
            cmd += ["--dtype", "bfloat16"]
        print("  " + " ".join(cmd))
        subprocess.run(cmd, check=True)
        if not args.keep_source:
            import shutil
            shutil.rmtree(src, ignore_errors=True)
        print(f"  -> {dest}")
    return 0


def cmd_doctor(args) -> int:
    s = _settings(args)
    print(f"kavi {__version__}")
    print(f"data dir        : {s.data_dir}")
    print(f"dpd.db          : {s.dpd_db} {'OK' if s.dpd_db.exists() else 'MISSING'}")
    print(f"deconstructor   : {s.decon_db if s.decon_db.exists() else s.decon_json} "
          f"{'OK' if s.decon_db.exists() or s.decon_json.exists() else 'MISSING (optional)'}")
    for label, path in (("translate model", s.translate_model), ("review model", s.eval_model)):
        print(f"{label:16}: {path} {'OK' if Path(path).expanduser().exists() else 'MISSING (kavi setup)'}")
    if s.dpd_db.exists():
        dpd = _dpd(s)
        print(f"DPD release     : {dpd.version}")
        a = dpd.analyse("bhikkhave")
        print(f"sample lookup   : bhikkhave -> {a.headwords[0].lemma if a.headwords else '?'}: {a.headwords[0].analysis if a.headwords else ''}")
    problems = s.check()
    print("\n".join("! " + p for p in problems) if problems else "all good")
    return 1 if problems else 0


def cmd_eval(args) -> int:
    """Score a translation against a reference translation (chrF, word F1, convention findings)."""
    from .evaluate import evaluate

    s = _settings(args)
    cand = Path(args.candidate).read_text(encoding="utf-8")
    ref = Path(args.reference).read_text(encoding="utf-8")
    src = Path(args.source).read_text(encoding="utf-8") if args.source else None
    dpd = _dpd(s) if src else None
    score = evaluate(cand, ref, src, dpd, s.glossary_map if src else None, s.glossary_alternatives if src else None)
    print(score.table())
    return 0


def cmd_app(args) -> int:
    app = Path(__file__).with_name("app.py")
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)] + (args.streamlit_args or []))


# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kavi", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"kavi {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--data-dir", help="folder holding dpd.db and deconstructor files (default: ./data)")

    t = sub.add_parser("translate", help="translate Markdown or plain text")
    common(t)
    t.add_argument("paths", nargs="*", help="input file(s) or directory")
    t.add_argument("--text", help="translate this string instead of a file")
    t.add_argument("-o", "--out", help="output file (or directory for several inputs); default stdout")
    t.add_argument("--table", help="also write the DPD word-analysis table (Markdown) here")
    t.add_argument("--report", help="also write the review report (issues and revisions per segment) here")
    t.add_argument("--rounds", type=int, help="review/revise rounds (default 5)")
    t.add_argument("--no-review", action="store_true", help="translate only, skip the review model")
    t.add_argument("--think", action="store_true", help="let the review model think before answering (slower)")
    t.add_argument("--no-cache", action="store_true", help="ignore and do not write the translation cache")
    t.add_argument("--translate-model", help="MLX path of the translation model")
    t.add_argument("--review-model", help="MLX path of the review model")
    t.add_argument("--max-tokens", type=int)
    t.add_argument("--sentence-words", type=int, help="translate paragraphs longer than this sentence by sentence")
    t.add_argument("--batch-words", type=int, help="review batches up to this many Pāli words")
    t.add_argument("--glossary", help="file of 'term: gloss' lines to keep in Pāli with a gloss (default: the built-in doctrinal glossary; 'none' to disable)")
    t.set_defaults(func=cmd_translate)

    a = sub.add_parser("analyse", aliases=["analyze"], help="DPD word-by-word analysis of a text")
    common(a)
    a.add_argument("words", nargs="*")
    a.add_argument("-f", "--file")
    a.add_argument("--json", action="store_true")
    a.add_argument("--pairs", action="store_true", help="print the reference lines given to the translate model")
    a.add_argument("--full", action="store_true", help="more homonyms per word")
    a.set_defaults(func=cmd_analyse)

    st = sub.add_parser("setup", help="download and convert the MITRA models to MLX")
    st.add_argument("--bits", type=int, default=0, choices=[4, 8, 0], help="quantisation: 0 = bfloat16 (default), 8 or 4 bits")
    st.add_argument("--translate-only", action="store_true")
    st.add_argument("--review-only", action="store_true")
    st.add_argument("--keep-source", action="store_true", help="keep the downloaded bf16 checkpoint")
    st.add_argument("--force", action="store_true")
    st.set_defaults(func=cmd_setup)

    d = sub.add_parser("doctor", help="check data files and models")
    common(d)
    d.add_argument("--translate-model")
    d.add_argument("--review-model")
    d.set_defaults(func=cmd_doctor)

    ev = sub.add_parser("eval", help="score a translation against a reference translation")
    common(ev)
    ev.add_argument("candidate", help="the translation to score (Markdown)")
    ev.add_argument("reference", help="the reference translation (Markdown)")
    ev.add_argument("--source", help="the Pāli source: enables the convention and glossary checks")
    ev.add_argument("--glossary")
    ev.set_defaults(func=cmd_eval)

    ap_ = sub.add_parser("app", help="run the Streamlit interface")
    ap_.add_argument("streamlit_args", nargs=argparse.REMAINDER)
    ap_.set_defaults(func=cmd_app)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

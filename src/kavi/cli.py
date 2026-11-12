"""Command line interface.

    kavi translate text.md -o text.en.md        # translate a Markdown or plain-text file
    kavi translate --text "Namo tassa …"         # translate a string
    kavi translate text.md --interlinear          # four lines per sentence: Pāḷi, analysis, glosses, translation
    echo "…" | kavi translate                    # or stdin
    kavi analyse "Ekaṃ samayaṃ bhagavā …"        # the DPD word-by-word table only
    kavi setup                                   # download the dictionaries and the model
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
    if getattr(args, "model", None):
        s.translate_model = args.model
        s.eval_model = args.model
    if getattr(args, "translate_model", None):
        s.translate_model = args.translate_model
    if getattr(args, "review_model", None):
        s.eval_model = args.review_model
    if getattr(args, "rounds", None) is not None:
        s.max_rounds = args.rounds
    if getattr(args, "think", False):
        s.thinking = True
    if getattr(args, "max_tokens", None):
        s.max_tokens = args.max_tokens
    if getattr(args, "batch_words", None):
        s.eval_batch_words = args.batch_words
    if getattr(args, "dual_resident", False):
        s.release_translator = False
    elif getattr(args, "release_translator", False):
        s.release_translator = True
    if getattr(args, "lang", None):
        s.use_language(args.lang)
    if getattr(args, "glossary", None):
        s.glossary = None if args.glossary.lower() == "none" else Path(args.glossary).expanduser()
    return s


def _dpd(s: Settings):
    """The lexicon of the language: the DPD for Pāli, vidyut and the Cologne dictionaries for Sanskrit."""
    from .language import set_language
    if s.lang == "sa":
        from .sanskrit import SanskritLexicon
        lexicon = SanskritLexicon(s.data_dir)
    else:
        from .dpd import DPD
        lexicon = DPD(s.dpd_db, s.decon_db, s.decon_json, cache_kb=s.sqlite_cache_kb)
    set_language(lexicon)                          # analyse and eval read the language record too, not only translate
    return lexicon


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
        if any("(optional" not in p for p in problems):      # only the deconstructor may be missing
            return 1
    dpd = _dpd(s)
    pool = ModelPool(s.translate_model, s.eval_model)
    tr = Translator(s, dpd, pool, use_cache=not args.no_cache)
    inputs: list[tuple[str, str | None, Path | None]] = []   # text, source name, path below the directory given
    if args.paths and len(args.paths) > 1 or (args.paths and Path(args.paths[0]).is_dir()):
        for raw in args.paths:
            p = Path(raw)
            files = sorted(p.rglob("*.md")) + sorted(p.rglob("*.txt")) if p.is_dir() else [p]
            inputs += [(f.read_text(encoding="utf-8"), str(f), f.relative_to(p) if p.is_dir() else Path(f.name)) for f in files]
    else:
        text, name = _read_input(args)
        inputs = [(text, name, Path(Path(name).name) if name else None)]
    many = len(inputs) > 1

    def target(arg: str, rel: Path | None, default: str, rename=lambda r: r) -> Path:
        """Where an output goes: the file named, or below the directory named for several inputs, keeping each
        input's sub-folder so that two files of one name do not overwrite each other."""
        out = Path(arg)
        if out.is_dir() or many:
            out = out / (rename(rel) if rel else default)
        out.parent.mkdir(parents=True, exist_ok=True)
        return out

    segments = None
    if getattr(args, "segments", None):
        from .interlinear import load_segments
        segments = []
        for raw in args.segments:
            segments.extend(load_segments(Path(raw)))
    for text, name, rel in inputs:
        if name:
            sys.stderr.write(f"== {name}\n")
        result = tr.translate_markdown(text, segments=segments, interlinear=bool(args.interlinear), review=s.max_rounds > 0)
        if args.out:
            out = target(args.out, rel, "translation.md", lambda r: r.with_name(r.stem + ".en" + r.suffix))
            out.write_text(result.markdown, encoding="utf-8")
            sys.stderr.write(f"   -> {out}\n")
        else:
            print(result.markdown)
        if args.first_pass_out and result.first_pass_en:
            out = target(args.first_pass_out, rel, "first_pass.en.md", lambda r: r.with_name(r.stem + ".first_pass.en.md"))
            out.write_text(result.first_pass_en, encoding="utf-8")
            sys.stderr.write(f"   first pass ref -> {out}\n")
        if args.en_out and result.en_markdown:
            out = target(args.en_out, rel, "translation.en.md")
            out.write_text(result.en_markdown, encoding="utf-8")
            sys.stderr.write(f"   normal en -> {out}\n")
        for arg, text_of, label in ((args.table, result.table, "word analysis"), (args.report, result.report, "review report")):
            if not arg:
                continue
            side = Path(arg)
            if many and rel:                           # one file per input, not the last input's alone
                side = side.with_name(f"{side.stem}.{'.'.join(rel.with_suffix('').parts)}{side.suffix}")
            side.parent.mkdir(parents=True, exist_ok=True)
            side.write_text(text_of(), encoding="utf-8")
            sys.stderr.write(f"   {label} -> {side}\n")
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


DPD_RELEASE_URL = "https://github.com/digitalpalidictionary/dpd-db/releases/latest/download/dpd.db.tar.xz"
DECONSTRUCTOR_URL = "https://raw.githubusercontent.com/digitalpalidictionary/deconstructor_output/main/deconstructor_output.json.tar.gz"


def _download_file(url: str, dest: Path) -> None:
    """Download a file with user-agent and progress output."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "kavi"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        chunk_size = 1024 * 1024
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                percent = done * 100 // total
                print(f"\r  {done // (1024 * 1024)} / {total // (1024 * 1024)} MB ({percent}%)", end="", flush=True)
            else:
                print(f"\r  {done // (1024 * 1024)} MB", end="", flush=True)
        print()


def _extract_tar(archive: Path, dest_dir: Path) -> None:
    import tarfile
    mode = "r:xz" if archive.name.endswith(".xz") else "r:gz" if archive.name.endswith(".gz") else "r:*"
    with tarfile.open(archive, mode) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(dest_dir, filter="data")
        else:
            tar.extractall(dest_dir)


def cmd_setup_dpd(args) -> int:
    """Download the latest Digital Pāḷi Dictionary (dpd.db) and deconstructor files from GitHub."""
    s = _settings(args)
    data = s.data_dir
    data.mkdir(parents=True, exist_ok=True)
    force = getattr(args, "force", False)

    db_dest = data / "dpd.db"
    if db_dest.exists() and not force:
        print(f"dpd.db present at {db_dest}")
    else:
        print(f"downloading latest dpd.db from {DPD_RELEASE_URL} …")
        archive = data / "dpd.db.tar.xz"
        try:
            _download_file(DPD_RELEASE_URL, archive)
            print(f"extracting {archive.name} …")
            _extract_tar(archive, data)
            print(f"dpd.db ready at {db_dest}")
        finally:
            if archive.exists() and not getattr(args, "keep_source", False):
                archive.unlink(missing_ok=True)

    decon_json = data / "deconstructor_output.json"
    decon_db = data / "deconstructor.sqlite"
    if (decon_db.exists() or decon_json.exists()) and not force:
        print(f"deconstructor present at {decon_db if decon_db.exists() else decon_json}")
    else:
        print(f"downloading deconstructor from {DECONSTRUCTOR_URL} …")
        archive = data / "deconstructor_output.json.tar.gz"
        try:
            _download_file(DECONSTRUCTOR_URL, archive)
            print(f"extracting {archive.name} …")
            _extract_tar(archive, data)
            print(f"deconstructor ready at {decon_json}")
        finally:
            if archive.exists() and not getattr(args, "keep_source", False):
                archive.unlink(missing_ok=True)

    if decon_json.exists() and (not decon_db.exists() or force):
        from .dpd import DPD
        decon_db.unlink(missing_ok=True)               # an existing index is opened as it is, never rebuilt
        print("indexing deconstructor into SQLite …")
        con = DPD._open_decon(decon_db, decon_json)
        if con:
            con.close()
        print(f"indexed {decon_db}")

    print("DPD setup complete.")
    return 0


def cmd_setup_sanskrit(args) -> int:
    """Download vidyut's linguistic data (81 MB, MIT) and the Cologne digitisations of Edgerton's Buddhist Hybrid
    Sanskrit Dictionary, Monier-Williams and Apte (CC BY-NC-SA 3.0), and build data/sanskrit.sqlite."""
    import urllib.request
    from . import cologne
    s = _settings(args)
    data = s.data_dir
    data.mkdir(parents=True, exist_ok=True)
    vdir = s.vidyut_dir
    force = getattr(args, "force", False)

    if s.sanskrit_db.exists() and (vdir / "kosha").exists() and not force:
        print(f"Sanskrit data present at {vdir} and {s.sanskrit_db}")
        return 0

    if (vdir / "kosha").exists() and not force:
        print(f"vidyut data present at {vdir}")
    else:
        import vidyut
        print(f"downloading vidyut's data to {vdir} …")
        vidyut.download_data(str(vdir))
    cdir = data / "cologne"
    cdir.mkdir(exist_ok=True)
    for d in cologne.SOURCES:
        dest = cdir / f"{d}.txt"
        if dest.exists() and not force:
            print(f"{dest.name} present")
            continue
        url = cologne.RAW.format(d=d)
        print(f"downloading {url} …")
        urllib.request.urlretrieve(url, dest)
    print("building sanskrit.sqlite …")
    out = cologne.build(data, progress=print)
    print(f"done: {out}")
    return 0


def cmd_setup_models(args) -> int:
    """Download the unified model checkpoint (default: Qwen-3.8-27B at hardware memory tier's precision)."""
    s = _settings(args)
    if getattr(args, "mitra", False) or getattr(args, "translate_only", False) or getattr(args, "review_only", False):
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

    model_id = getattr(args, "model", None)
    if not model_id:
        bits = getattr(args, "bits", 0)
        if bits == 4:
            model_id = "mlx-community/Qwen3.8-27B-4bit"
        elif bits == 8:
            model_id = "mlx-community/Qwen3.8-27B-8bit"
        else:
            model_id = s.model

    print(f"setting up unified model: {model_id} …")
    from huggingface_hub import snapshot_download
    snapshot_download(model_id, max_workers=8)
    print(f"unified model ready: {model_id}")
    return 0


def cmd_setup(args) -> int:
    """Set up language data and models. By default sets up everything (DPD, Sanskrit, models)."""
    do_dpd = getattr(args, "dpd", False)
    do_sa = getattr(args, "sanskrit", False)
    do_models = (
        getattr(args, "models", False)
        or getattr(args, "translate_only", False)
        or getattr(args, "review_only", False)
    )

    # If no specific component was selected, or --all was specified, include everything
    if not (do_dpd or do_sa or do_models) or getattr(args, "all", False):
        do_dpd = True
        do_sa = True
        do_models = True

    if do_dpd:
        ret = cmd_setup_dpd(args)
        if ret != 0:
            return ret

    if do_sa:
        ret = cmd_setup_sanskrit(args)
        if ret != 0:
            return ret

    if do_models:
        ret = cmd_setup_models(args)
        if ret != 0:
            return ret

    return 0


def cmd_doctor(args) -> int:
    s = _settings(args)
    print(f"kavi {__version__}")
    print(f"data dir        : {s.data_dir}")

    langs = [args.lang] if getattr(args, "lang", None) else ["pi", "sa"]
    problems = []

    if "pi" in langs:
        print("\nPāli (DPD):")
        dpd_ok = s.dpd_db.exists()
        decon_ok = s.decon_db.exists() or s.decon_json.exists()
        print(f"  dpd.db          : {s.dpd_db} {'OK' if dpd_ok else 'MISSING (kavi setup --dpd)'}")
        print(f"  deconstructor   : {s.decon_db if s.decon_db.exists() else s.decon_json} "
              f"{'OK' if decon_ok else 'MISSING (kavi setup --dpd)'}")
        if not dpd_ok:
            problems.append(f"dpd.db not found at {s.dpd_db} — run `kavi setup --dpd`")
        if not decon_ok:
            problems.append(f"deconstructor not found in {s.data_dir} — run `kavi setup --dpd`")
        if dpd_ok:
            try:
                from .dpd import DPD
                dpd = DPD(s.dpd_db, s.decon_db, s.decon_json)
                print(f"  lexicon         : {dpd.version}")
                sample = "bhikkhave"
                a = dpd.analyse(sample)
                lemma = a.headwords[0].lemma if a.headwords else "?"
                analysis = a.headwords[0].analysis if a.headwords else ""
                print(f"  sample lookup   : {sample} -> {lemma}: {analysis}")
            except Exception as e:
                problems.append(f"dpd lookup error: {e}")

    if "sa" in langs:
        print("\nSanskrit (vidyut + Cologne dictionaries):")
        vidyut_ok = (s.vidyut_dir / "kosha").exists()
        sa_ok = s.sanskrit_db.exists()
        print(f"  vidyut data     : {s.vidyut_dir} {'OK' if vidyut_ok else 'MISSING (kavi setup --sanskrit)'}")
        print(f"  sanskrit.sqlite : {s.sanskrit_db} {'OK' if sa_ok else 'MISSING (kavi setup --sanskrit)'}")
        if not vidyut_ok:
            problems.append(f"vidyut data not found at {s.vidyut_dir} — run `kavi setup --sanskrit`")
        if not sa_ok:
            problems.append(f"sanskrit.sqlite not found at {s.sanskrit_db} — run `kavi setup --sanskrit`")
        if vidyut_ok and sa_ok:
            try:
                from .sanskrit import SanskritLexicon
                sa_lex = SanskritLexicon(s.data_dir)
                sample = "bodhisattvaḥ"
                a = sa_lex.analyse(sample)
                lemma = a.headwords[0].lemma if a.headwords else "?"
                analysis = a.headwords[0].analysis if a.headwords else ""
                print(f"  sample lookup   : {sample} -> {lemma}: {analysis}")
            except Exception as e:
                problems.append(f"sanskrit lookup error: {e}")

    print("\nModels:")
    if s.translate_model == s.eval_model:
        path = s.model
        ok = Path(path).expanduser().exists() or path.startswith("buddhist-nlp/") or path.startswith("mlx-community/")
        print(f"  unified model   : {path} {'OK' if ok else 'MISSING (kavi setup)'}")
        if not ok:
            problems.append(f"unified model not found at {path} — run `kavi setup`")
    else:
        for label, path in (("translate model", s.translate_model), ("review model", s.eval_model)):
            ok = Path(path).expanduser().exists() or path.startswith("buddhist-nlp/") or path.startswith("mlx-community/")
            print(f"  {label:16}: {path} {'OK' if ok else 'MISSING (kavi setup)'}")
            if not ok:
                problems.append(f"{label} not found at {path} — run `kavi setup`")

    from .config import system_ram_gb, memory_tier
    ram_gb = system_ram_gb()
    tier = memory_tier()
    print(f"\nHardware & Memory:")
    print(f"  system RAM      : {ram_gb} GB unified memory (Tier: {tier})")
    two = s.translate_model != s.eval_model
    print(f"  model residency : {'one model for both roles' if not two else 'two models resident together' if not s.release_translator else 'two models, one at a time'}")
    print(f"  sqlite cache    : {s.sqlite_cache_kb // 1024} MB")
    if tier == "32GB":
        print("  recommendation  : 32GB tier — consider 8-bit or 4-bit quantisation (`kavi setup --bits 8`)")
    elif tier == "64GB":
        print("  recommendation  : 64GB tier — bf16 single/sequential model runs comfortably; 8-bit for instant dual residency")
    else:
        print("  recommendation  : 128GB tier — dual bf16 residency enabled (zero reload latency)")

    print()
    if problems:
        print("\n".join("! " + p for p in problems))
    else:
        print("all good")
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
        p.add_argument("--lang", choices=["pi", "sa"], help="the source language: pi Pāli (default), sa Sanskrit or Buddhist Hybrid Sanskrit")

    t = sub.add_parser("translate", help="translate Markdown or plain text")
    common(t)
    t.add_argument("paths", nargs="*", help="input file(s) or directory")
    t.add_argument("--text", help="translate this string instead of a file")
    t.add_argument("-o", "--out", help="output file (or directory for several inputs); default stdout")
    t.add_argument("--table", help="also write the DPD word-analysis table (Markdown) here")
    t.add_argument("--report", help="also write the review report (issues and revisions per segment) here")
    t.add_argument("--rounds", type=int, help="review/revise rounds (default 5)")
    t.add_argument("--first-pass", dest="first_pass_out", help="also write the initial discourse macro-pass (first pass reference) to this file")
    t.add_argument("--think", action="store_true", help="let the review model think before answering (slower)")
    t.add_argument("--no-cache", action="store_true", help="ignore and do not write the translation cache")
    t.add_argument("--model", help="single model to use for both roles (translate and review)")
    t.add_argument("--translate-model", help="MLX path of the translation model")
    t.add_argument("--review-model", help="MLX path of the review model")
    t.add_argument("--max-tokens", type=int)
    t.add_argument("--batch-words", type=int, help="review batches up to this many Pāli words")
    t.add_argument("--dual-resident", action="store_true", help="keep two different translate and review models resident together (for >= 128GB Macs)")
    t.add_argument("--release-translator", action="store_true", help="with two different models, free the translator before the review, which then revises by itself (the default on <= 64GB Macs)")
    t.add_argument("--glossary", help="file of 'term: gloss' lines to keep in Pāli with a gloss (default: the built-in doctrinal glossary; 'none' to disable)")
    t.add_argument("--interlinear", action="store_true",
                   help="interlinear output: for each sentence the Pāḷi, the analysis in the textbook's symbols, the glosses and the translation")
    t.add_argument("--en", "--en-out", dest="en_out",
                   help="also write the normal English translation (reconstructed from the interlinear) to this file or directory")
    t.add_argument("--segments", nargs="*", help="SuttaCentral segment JSON file(s): the sentences and their numbers follow them")
    t.set_defaults(func=cmd_translate)

    a = sub.add_parser("analyse", aliases=["analyze"], help="DPD word-by-word analysis of a text")
    common(a)
    a.add_argument("words", nargs="*")
    a.add_argument("-f", "--file")
    a.add_argument("--json", action="store_true")
    a.add_argument("--pairs", action="store_true", help="print the reference lines given to the translate model")
    a.add_argument("--full", action="store_true", help="more homonyms per word")
    a.set_defaults(func=cmd_analyse)

    st = sub.add_parser("setup", help="download language data and set up models (all by default)")
    common(st)
    st.add_argument("--model", help="unified model to download/setup (default: Qwen-3.8-27B according to memory tier)")
    st.add_argument("--mitra", action="store_true", help="set up legacy MITRA models")
    st.add_argument("--bits", type=int, default=0, choices=[4, 8, 0], help="quantisation: 0 = bfloat16 (default), 8 or 4 bits")
    st.add_argument("--translate-only", action="store_true")
    st.add_argument("--review-only", action="store_true")
    st.add_argument("--keep-source", action="store_true", help="keep the downloaded bf16 checkpoint or data archives")
    st.add_argument("--force", action="store_true")
    st.add_argument("--models", action="store_true", help="set up models only")
    st.add_argument("--sanskrit", action="store_true", help="set up Sanskrit data only (vidyut and Cologne dictionaries)")
    st.add_argument("--dpd", "--pali", dest="dpd", action="store_true", help="set up Digital Pāḷi Dictionary data only (dpd.db and deconstructor)")
    st.add_argument("--all", action="store_true", help="set up everything (default)")
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

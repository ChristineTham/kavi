"""Bake-off: run several models as translator and as reviewer on the same passages and lay the results side by side.

    uv run python tools/bakeoff.py tests/samples/dn15-short.md \
        --model ~/.cache/mlx-models/mitra-qwen35-translate-mlx-bf16:translate \
        --model ~/.cache/mlx-models/mitra-qwen35-it-mlx-bf16:both \
        --model ~/.cache/mlx-models/Qwen3.8-27B-8bit:both -o bakeoff.md

Each model is loaded once and freed before the next. As translator it gets the generic instruction prompt (or
MITRA's own prompt for the mitra-translate model) with the DPD analysis; the checker then runs on its draft and
the remaining findings are counted. As reviewer it gets the first translator's checked draft with the checker's
open findings, and the report shows what it reported, what it changed, and whether the open findings were resolved.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kavi.config import Settings  # noqa: E402
from kavi.dpd import DPD, analyse_text  # noqa: E402
from kavi.lint import lint  # noqa: E402
from kavi.models import (MLXModel, is_mitra_translate, parse_review, review_prompt, strip_wrapper,  # noqa: E402
                         translate_messages_generic, translate_prompt)
from kavi.segment import parse_markdown  # noqa: E402


def load(path: str) -> MLXModel:
    return MLXModel(path, log=lambda m: sys.stderr.write(m + "\n"))


def free(model: MLXModel) -> None:
    import mlx.core as mx
    del model.model, model.tokenizer
    gc.collect()
    mx.clear_cache()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("--model", action="append", required=True, help="path[:translate|review|both]")
    ap.add_argument("-o", "--out", default="bakeoff.md")
    ap.add_argument("--think", action="store_true", help="enable thinking for non-MITRA models")
    ap.add_argument("--max-tokens", type=int, default=2048)
    args = ap.parse_args()

    s = Settings()
    dpd = DPD(s.dpd_db, s.decon_db, s.decon_json)
    text = Path(args.sample).read_text(encoding="utf-8")
    paras = [b for b in parse_markdown(text) if b.kind in ("para", "list") and b.text.strip() and len(b.text.split()) > 3]
    sources = [b.text for b in paras]
    if not sources:
        sys.exit("no paragraphs found in the sample")
    analyses = [analyse_text(dpd, src) for src in sources]
    specs = []
    for m in args.model:
        path, _, role = m.rpartition(":") if ":" in m and not m.endswith((".mdx", ".md")) else (m, "", "both")
        role = role or "both"
        specs.append((str(Path(path).expanduser()), role))

    results: dict[str, dict] = {}       # model name -> {"translate": [(text, seconds, findings)], "review": [...]}
    reference: list[str] | None = None  # the first translator's checked drafts, reviewed by everyone

    for path, role in specs:
        name = Path(path).name
        model = load(path)
        think = args.think and not name.lower().startswith("mitra")
        results[name] = {}
        if role in ("translate", "both"):
            outs = []
            for src, an in zip(sources, analyses):
                t0 = time.time()
                if is_mitra_translate(path):
                    msgs = [{"role": "user", "content": translate_prompt(src, an, False, False, extra_terms=s.glossary_terms, glossary=s.glossary_map)}]
                else:
                    msgs = translate_messages_generic(src, an, False, False, extra_terms=s.glossary_terms, glossary=s.glossary_map)
                r = model.chat(msgs, max_tokens=args.max_tokens, thinking=think)
                draft = strip_wrapper(r.text)
                fixed, findings = lint(an, draft, s.glossary_map)
                outs.append({"draft": draft, "checked": fixed, "findings": findings, "seconds": time.time() - t0,
                             "tokens": r.tokens, "thinking": len(r.thinking)})
                sys.stderr.write(f"  [{name} translate] {time.time() - t0:.0f}s {r.tokens} tok\n")
            results[name]["translate"] = outs
            if reference is None:
                reference = [o["checked"] for o in outs]
                ref_findings = [[f for f in o["findings"] if f.severity == "ask"] for o in outs]
        if role in ("review", "both") and reference is not None:
            outs = []
            for i, (src, an) in enumerate(zip(sources, analyses)):
                t0 = time.time()
                known = {1: [str(f) for f in ref_findings[i]]} if ref_findings[i] else None
                prompt = review_prompt([(src, reference[i])], an, extra_terms=s.glossary_terms, glossary=s.glossary_map, known=known)
                r = model.chat([{"role": "system", "content": "You are a meticulous reviewer of Pāli-to-English translations."},
                                {"role": "user", "content": prompt}], max_tokens=args.max_tokens * 2, thinking=think)
                res = parse_review(r.text, 1)
                revised = res.revised.get(1, "")
                after, findings = lint(an, revised, s.glossary_map) if revised else (reference[i], ref_findings[i])
                outs.append({"issues": res.issues, "revised": after, "parsed": res.parsed, "seconds": time.time() - t0,
                             "open": [f for f in findings if f.severity == "ask"], "raw": r.text[:1500], "thinking": len(r.thinking)})
                sys.stderr.write(f"  [{name} review] {time.time() - t0:.0f}s parsed={res.parsed} issues={len(res.issues)}\n")
            results[name]["review"] = outs
        free(model)

    # ---- report
    lines = [f"# Bake-off on `{Path(args.sample).name}`", "",
             f"{len(sources)} paragraphs; glossary: {Path(str(s.glossary)).name}; thinking: {'on' if args.think else 'off'} (non-MITRA models)", ""]
    lines.append("## As translator\n")
    lines.append("| model | mean s/para | tokens | checker findings left (ask) | checker fixes applied |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, res in results.items():
        if "translate" in res:
            outs = res["translate"]
            asks = sum(1 for o in outs for f in o["findings"] if f.severity == "ask")
            fixes = sum(1 for o in outs for f in o["findings"] if f.severity == "fix")
            lines.append(f"| {name} | {sum(o['seconds'] for o in outs) / len(outs):.0f} | {sum(o['tokens'] for o in outs)} | {asks} | {fixes} |")
    for i, src in enumerate(sources):
        lines.append(f"\n### Paragraph {i + 1}\n\n> {src}\n")
        for name, res in results.items():
            if "translate" in res:
                o = res["translate"][i]
                lines.append(f"**{name}** ({o['seconds']:.0f}s)\n\n{o['checked']}\n")
                if o["draft"] != o["checked"]:
                    lines.append(f"<details><summary>raw draft and checker</summary>\n\n{o['draft']}\n\n" +
                                 "\n".join(f"- {'fixed' if f.severity == 'fix' else 'open'}: {f}" for f in o["findings"]) + "\n\n</details>\n")
                elif o["findings"]:
                    lines.append("- " + "\n- ".join(f"open: {f}" for f in o["findings"]) + "\n")
    lines.append("\n## As reviewer (of the first translator's checked draft)\n")
    lines.append("| model | mean s/para | parsed | issues reported | open findings resolved |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, res in results.items():
        if "review" in res:
            outs = res["review"]
            before = sum(len(x) for x in ref_findings)
            after = sum(len(o["open"]) for o in outs)
            lines.append(f"| {name} | {sum(o['seconds'] for o in outs) / len(outs):.0f} | {sum(o['parsed'] for o in outs)}/{len(outs)} | "
                         f"{sum(len(o['issues']) for o in outs)} | {before - after}/{before} |")
    for i, src in enumerate(sources):
        lines.append(f"\n### Paragraph {i + 1} — reviewed draft\n\n{reference[i] if reference else ''}\n")
        if ref_findings[i]:
            lines.append("Open findings handed to the reviewer:\n" + "\n".join(f"- {f}" for f in ref_findings[i]) + "\n")
        for name, res in results.items():
            if "review" in res:
                o = res["review"][i]
                lines.append(f"**{name}** ({o['seconds']:.0f}s; issues: {len(o['issues'])}; still open: {len(o['open'])})\n")
                lines.extend(f"- {iss}" for iss in o["issues"])
                lines.append(f"\nRevised: {o['revised']}\n")
                if not o["parsed"]:
                    lines.append(f"<details><summary>unparsed output</summary>\n\n```\n{o['raw']}\n```\n\n</details>\n")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    sys.stderr.write(f"-> {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

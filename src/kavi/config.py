"""Paths and tunables. Every value can be overridden by an environment variable or a CLI flag."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = Path(os.environ.get("KAVI_MODELS_DIR", HOME / ".cache" / "mlx-models"))

TRANSLATE_HF = "buddhist-nlp/mitra-qwen35-translate"
IT_HF = "buddhist-nlp/mitra-qwen35-it"
TRANSLATE_MLX = "mitra-qwen35-translate-mlx-bf16"
IT_MLX = "mitra-qwen35-it-mlx-bf16"


def _data_dir() -> Path:
    env = os.environ.get("KAVI_DATA_DIR")
    if env:
        return Path(env).expanduser()
    for candidate in (REPO_ROOT / "data", HOME / ".cache" / "kavi" / "data"):
        if (candidate / "dpd.db").exists():
            return candidate
    return REPO_ROOT / "data"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=_data_dir)
    translate_model: str = os.environ.get("KAVI_TRANSLATE_MODEL", str(MODELS_DIR / TRANSLATE_MLX))
    eval_model: str = os.environ.get("KAVI_EVAL_MODEL", str(MODELS_DIR / IT_MLX))
    max_rounds: int = 5            # review/revise rounds per batch (0 = translate only)
    max_tokens: int = 2048         # generation cap per model call
    sentence_words: int = 60       # a paragraph longer than this is translated sentence by sentence
    eval_batch_words: int = 400    # paragraphs are reviewed together up to this many Pāḷi words
    thinking: bool = False         # let the instruction-tuned model think before it answers
    release_translator: bool = True  # free the translate model before the review phase (two large models rarely fit)
    context_segments: int = 2      # preceding segments shown to the translate model, for consistent formulas
    temperature: float = 0.0
    cache_dir: Path = HOME / ".cache" / "kavi"
    glossary: Path | None = Path(__file__).with_name("glossaries") / "default.txt"   # "term: gloss" lines; None disables

    def _glossary_lines(self) -> list[tuple[str, str, list[str]]]:
        """(stem, gloss, alternatives) per glossary line "stem: gloss | alt1, alt2"."""
        if not self.glossary or not Path(self.glossary).exists():
            return []
        out = []
        for line in Path(self.glossary).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            term, _, rest = line.partition(":")
            rest = rest.split("#")[0]                      # a trailing comment
            gloss, _, alts = rest.partition("|")
            if term.strip():
                out.append((term.strip().strip("`"), gloss.strip(), [a.strip() for a in alts.split(",") if a.strip()]))
        return out

    @property
    def glossary_map(self) -> dict[str, str]:
        """stem -> gloss from the glossary file, if any."""
        return {stem: gloss for stem, gloss, _ in self._glossary_lines()}

    @property
    def glossary_alternatives(self) -> dict[str, list[str]]:
        """stem -> other English renderings of the term that must give way to the gloss."""
        return {stem: alts for stem, _, alts in self._glossary_lines() if alts}

    @property
    def glossary_terms(self) -> list[str]:
        """"term (gloss)" strings from the glossary file, if any (a term without a gloss is left to the translator)."""
        return [f"{t} ({g})" for t, g in self.glossary_map.items() if g]

    @property
    def dpd_db(self) -> Path:
        return Path(os.environ.get("KAVI_DPD_DB", self.data_dir / "dpd.db")).expanduser()

    @property
    def decon_db(self) -> Path:
        return self.data_dir / "deconstructor.sqlite"

    @property
    def decon_json(self) -> Path:
        return self.data_dir / "deconstructor_output.json"

    def check(self) -> list[str]:
        """Human-readable list of what is missing."""
        problems = []
        if not self.dpd_db.exists():
            problems.append(f"dpd.db not found at {self.dpd_db} — download the DPD SQLite release "
                            "(https://github.com/digitalpalidictionary/dpd-db/releases) into the data folder "
                            "or set KAVI_DPD_DB")
        if not self.decon_db.exists() and not self.decon_json.exists():
            problems.append(f"deconstructor_output.json not found in {self.data_dir} (optional: sandhi splitting "
                            "then relies on the lookup table and Kaccāyana heuristics alone)")
        for label, path in (("translate model", self.translate_model), ("review model", self.eval_model)):
            if "/" in path and not Path(path).expanduser().exists() and not path.startswith("buddhist-nlp/"):
                problems.append(f"{label} not found at {path} — run `kavi setup`")
        return problems

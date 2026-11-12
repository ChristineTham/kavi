"""Paths and tunables. Every value can be overridden by an environment variable or a CLI flag."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = Path(os.environ.get("KAVI_MODELS_DIR", HOME / ".cache" / "mlx-models"))

DEFAULT_MODEL_BASE = "mlx-community/Qwen3.8-27B"
TRANSLATE_HF = "buddhist-nlp/mitra-qwen35-translate"
IT_HF = "buddhist-nlp/mitra-qwen35-it"
TRANSLATE_MLX = "mitra-qwen35-translate-mlx-bf16"
IT_MLX = "mitra-qwen35-it-mlx-bf16"


def system_ram_gb() -> int:
    """Detect total system unified memory in gigabytes (e.g. 32, 64, 128)."""
    try:
        import subprocess
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
        return int(out) // (1024 ** 3)
    except Exception:
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // (1024 ** 3)
    except Exception:
        return 64


def default_model() -> str:
    """Return default MLX model identifier based on system unified memory.
    Always use unquantised (bf16) on >= 100 GB RAM (128GB tier), 8-bit on >= 50 GB (64GB tier),
    and 4-bit on < 50 GB (32GB tier).
    """
    env = os.environ.get("KAVI_MODEL")
    if env:
        return env
    ram = system_ram_gb()
    if ram >= 100:
        return f"{DEFAULT_MODEL_BASE}-bf16"
    elif ram >= 50:
        return f"{DEFAULT_MODEL_BASE}-8bit"
    return f"{DEFAULT_MODEL_BASE}-4bit"


def memory_tier() -> str:
    """Return '32GB', '64GB', or '128GB' based on system RAM."""
    ram = system_ram_gb()
    if ram <= 40:
        return "32GB"
    elif ram <= 80:
        return "64GB"
    return "128GB"


def _default_release_translator() -> bool:
    """On machines with >= 90 GB RAM (128GB tier), keep both models resident for 0s turnaround."""
    env = os.environ.get("KAVI_RELEASE_TRANSLATOR")
    if env is not None:
        return env.lower() not in ("0", "false", "no")
    return system_ram_gb() < 90


def _default_sqlite_cache_kb() -> int:
    """Tune SQLite cache size by memory tier: 32MB for 32GB, 64MB for 64GB, 256MB for 128GB."""
    tier = memory_tier()
    if tier == "32GB":
        return 32768
    elif tier == "64GB":
        return 65536
    return 262144


def _data_dir() -> Path:
    env = os.environ.get("KAVI_DATA_DIR")
    if env:
        return Path(env).expanduser()
    for candidate in (REPO_ROOT / "data", HOME / ".cache" / "kavi" / "data"):
        if (candidate / "dpd.db").exists():
            return candidate
    return REPO_ROOT / "data"


_GLOSSARY_CACHE: dict = {}


@dataclass
class Settings:
    data_dir: Path = field(default_factory=_data_dir)
    model: str = field(default_factory=default_model)
    translate_model: str = ""
    eval_model: str = ""
    max_rounds: int = 5            # review/revise rounds per batch (0 = translate only)
    max_tokens: int = 2048         # generation cap per model call
    eval_batch_words: int = 400    # paragraphs are reviewed together up to this many Pāḷi words
    thinking: bool = False         # let the instruction-tuned model think before it answers
    release_translator: bool = field(default_factory=_default_release_translator)  # True on <=64GB, False on 128GB
    sqlite_cache_kb: int = field(default_factory=_default_sqlite_cache_kb)
    metal_cache_interval: int = 10 # clear Metal cache every N segments during generation
    context_segments: int = 2      # preceding segments shown to the translate model, for consistent formulas
    temperature: float = 0.0
    cache_dir: Path = HOME / ".cache" / "kavi"
    lang: str = "pi"               # "pi" Pāli (the Digital Pāḷi Dictionary) or "sa" Sanskrit (vidyut and the Cologne dictionaries)
    glossary: Path | None = Path(__file__).with_name("glossaries") / "default.txt"   # "term: gloss" lines; None disables

    def __post_init__(self) -> None:
        if not self.translate_model:
            self.translate_model = os.environ.get("KAVI_TRANSLATE_MODEL", self.model)
        if not self.eval_model:
            self.eval_model = os.environ.get("KAVI_EVAL_MODEL", self.model)

    def use_language(self, lang: str) -> None:
        """Switch the language; the default glossary follows it unless one was given."""
        default = Path(__file__).with_name("glossaries")
        if self.glossary in (default / "default.txt", default / "sanskrit.txt", None) and self.glossary is not None:
            self.glossary = default / ("sanskrit.txt" if lang == "sa" else "default.txt")
        self.lang = lang

    def _glossary_lines(self) -> list[tuple[str, str, list[str]]]:
        """(stem, gloss, alternatives) per glossary line "stem: gloss | alt1, alt2"."""
        if not self.glossary or not Path(self.glossary).exists():
            return []
        path = Path(self.glossary)
        stamp = (str(path), path.stat().st_mtime_ns)       # read once, and again only when the file changes
        if _GLOSSARY_CACHE.get("stamp") == stamp:
            return _GLOSSARY_CACHE["lines"]
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            term, _, rest = line.partition(":")
            rest = rest.split("#")[0]                      # a trailing comment
            gloss, _, alts = rest.partition("|")
            if term.strip():
                out.append((term.strip().strip("`"), gloss.strip(), [a.strip() for a in alts.split(",") if a.strip()]))
        _GLOSSARY_CACHE.update(stamp=stamp, lines=out)
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
    def sanskrit_db(self) -> Path:
        return self.data_dir / "sanskrit.sqlite"

    @property
    def vidyut_dir(self) -> Path:
        return self.data_dir / "vidyut"

    @property
    def dpd_db(self) -> Path:
        return Path(os.environ.get("KAVI_DPD_DB", self.data_dir / "dpd.db")).expanduser()

    @property
    def decon_db(self) -> Path:
        return self.data_dir / "deconstructor.sqlite"

    @property
    def decon_json(self) -> Path:
        return self.data_dir / "deconstructor_output.json"

    def check(self, all_languages: bool = False) -> list[str]:
        """Human-readable list of what is missing."""
        problems = []
        langs = ["pi", "sa"] if all_languages else [self.lang]
        if "sa" in langs:
            if not (self.vidyut_dir / "kosha").exists():
                problems.append(f"vidyut data not found at {self.vidyut_dir} — run `kavi setup --sanskrit`")
            if not self.sanskrit_db.exists():
                problems.append(f"sanskrit.sqlite not found at {self.sanskrit_db} — run `kavi setup --sanskrit`")
        if "pi" in langs:
            if not self.dpd_db.exists():
                problems.append(f"dpd.db not found at {self.dpd_db} — download the DPD SQLite release "
                                "(https://github.com/digitalpalidictionary/dpd-db/releases) into the data folder "
                                "or set KAVI_DPD_DB (or run `kavi setup --dpd`)")
            if not self.decon_db.exists() and not self.decon_json.exists():
                problems.append(f"deconstructor_output.json not found in {self.data_dir} (optional: sandhi splitting "
                                "then relies on the lookup table and Kaccāyana heuristics alone)")
        for label, path in (("model", self.model), ("translate model", self.translate_model), ("review model", self.eval_model)):
            if not path:
                continue
            if "/" in path and not Path(path).expanduser().exists() and not (path.startswith("buddhist-nlp/") or path.startswith("mlx-community/")):
                problems.append(f"{label} not found at {path} — run `kavi setup`")
        return problems

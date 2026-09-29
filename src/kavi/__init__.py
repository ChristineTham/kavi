"""Kavi — a literal Pāḷi-to-English translator.

Pipeline: Markdown is cut into paragraphs and sentences; every word is resolved (sandhi undone with the
Digital Pāḷi Dictionary's deconstructor and Kaccāyana's sandhi rules) and looked up in the DPD; the
word-by-word analysis is handed to MITRA-QWEN as reference material for a literal translation; the
instruction-tuned MITRA model then reviews the draft against the same analysis and revises it, up to a
fixed number of rounds. Everything runs locally under MLX.
"""

__version__ = "0.1.0"

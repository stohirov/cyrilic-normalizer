"""Uzbek text normalization and Cyrillic→Latin transliteration for TTS.

Typical use — accept anything, emit the current standard::

    >>> from uztext import normalize
    >>> normalize("Ўзбекистон Республикаси")
    'Oʻzbekiston Respublikasi'

Emit a different orthography::

    >>> from uztext import normalize, LatinScheme
    >>> normalize("O'zbekiston", LatinScheme.LATIN_2026)
    'Ózbekiston'
"""

from .mappings import LatinScheme
from .normalizer import (
    cyrillic_to_latin,
    fold_latin_variants,
    normalize,
    normalize_unicode,
    render,
)

__all__ = [
    "LatinScheme",
    "cyrillic_to_latin",
    "fold_latin_variants",
    "normalize",
    "normalize_unicode",
    "render",
]

__version__ = "0.1.0"

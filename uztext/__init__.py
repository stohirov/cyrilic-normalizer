"""Uzbek text normalization and Cyrillic-to-Latin transliteration for TTS.

Accept any script and any orthography, emit exactly one. The default output is
the 1995 standard; see README.md for the scheme comparison table.

Doctests spell non-ASCII characters as escapes so that every comment and
docstring in this package stays pure ASCII.

Typical use::

    >>> from uztext import normalize
    >>> normalize("O'zbekiston Respublikasi") == "O\\u02bbzbekiston Respublikasi"
    True

Emit a different orthography::

    >>> from uztext import normalize, LatinScheme
    >>> normalize("O'zbekiston", LatinScheme.LATIN_2026) == "\\u00d6zbekiston"
    True
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

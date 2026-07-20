"""Table-driven Uzbek text normalizer and Cyrillic→Latin transliterator.

The pipeline has four stages, each exposed as a pure function:

1. :func:`normalize_unicode` — NFC + whitespace/dash cleanup.
2. :func:`cyrillic_to_latin` — Cyrillic → internal canonical Latin
   (a no-op for text that contains no Cyrillic, so mixed-script input works).
3. :func:`fold_latin_variants` — *every* known Latin spelling → internal
   canonical form.
4. :func:`render` — internal canonical form → the requested orthography.

:func:`normalize` chains all four and is the entry point for the TTS front-end.

No function mutates global state; all of them take a string and return a string.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Match, Pattern, Tuple

from .mappings import (
    APOSTROPHE_VARIANTS,
    CYRILLIC_ALPHABET,
    CYRILLIC_E_IOTATED,
    CYRILLIC_E_PLAIN,
    CYRILLIC_HARD_SIGN_EDGE,
    CYRILLIC_HARD_SIGN_MEDIAL,
    CYRILLIC_SIGNS,
    CYRILLIC_TO_LATIN,
    CYRILLIC_TS_INITIAL,
    CYRILLIC_TS_MEDIAL,
    CYRILLIC_VOWELS,
    LATIN_FOLD_BARE_C,
    LATIN_FOLD_TABLE,
    MODIFIER_APOSTROPHE,
    RENDER_TABLES,
    TURNED_COMMA,
    LatinScheme,
)

__all__ = [
    "LatinScheme",
    "normalize_unicode",
    "cyrillic_to_latin",
    "fold_latin_variants",
    "render",
    "normalize",
]


# --------------------------------------------------------------------------
# Generic table-driven replacement engine
# --------------------------------------------------------------------------


def _match_case(source: str, target: str, next_char: str = "", prev_char: str = "") -> str:
    """Re-apply the casing of ``source`` to ``target``.

    A single-character source (``Ş``, ``Ó``, ``Ч``) is genuinely ambiguous
    between title case and all caps, so the neighbours decide: look right
    first, and fall back to looking left when the match sits at the end of a
    word.

    ==================  ==========  ==========  ==========  ========
    source              prev_char   next_char   target      result
    ==================  ==========  ==========  ==========  ========
    ``ş`` (lower)       —           —           ``sh``      ``sh``
    ``Ş``               —           ``a``       ``sh``      ``Sh``
    ``Ş``               —           ``A``       ``sh``      ``SH``
    ``Ч`` (in ``ЁҒОЧ``) ``О``       —           ``ch``      ``CH``
    ``Ш`` (in ``Ш.``)   —           ``.``       ``sh``      ``Sh``
    ``SH``              —           —           ``ş``       ``Ş``
    ==================  ==========  ==========  ==========  ========

    Caseless characters in ``source`` (e.g. the modifier letter ``ʻ`` in
    ``Oʻ``) are ignored when deciding the case.
    """
    if not target:
        return target

    title = target[:1].upper() + target[1:].lower()

    cased = [c for c in source if c.isupper() or c.islower()]
    if not cased or all(c.islower() for c in cased):
        return target.lower()

    if all(c.isupper() for c in cased):
        if len(cased) > 1:
            # "SH" -> the whole match was capitals: keep shouting.
            return target.upper()
        # A single capital. "Şahar" vs "ŞAHAR": the letter to the right wins.
        if next_char.isupper():
            return target.upper()
        if next_char.islower():
            return title
        # No cased letter to the right ("ЁҒОЧ", "Ш.") -> ask the left.
        return target.upper() if prev_char.isupper() else title

    # Mixed, e.g. "Sh" or "Oʻ" -> title case.
    return title


def _compile_table(pairs: Iterable[Tuple[str, str]]) -> Tuple[Pattern[str], Dict[str, str]]:
    """Compile ``(source, target)`` pairs into a longest-match-first regex.

    The lookup dict is keyed on the NFC-normalized *lower-cased* source, which
    is what the substitution callback uses after case-folding the match.
    """
    lookup: Dict[str, str] = {}
    for source, target in pairs:
        key = unicodedata.normalize("NFC", source).lower()
        lookup.setdefault(key, target)

    # Longest first so digraphs and o+apostrophe beat single characters.
    alternatives = sorted(lookup, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(a) for a in alternatives), re.IGNORECASE)
    return pattern, lookup


def _apply_table(text: str, compiled: Tuple[Pattern[str], Dict[str, str]]) -> str:
    """Apply a compiled table to ``text``, preserving casing."""
    pattern, lookup = compiled
    if not text:
        return text

    def _replace(match: Match[str]) -> str:
        source = match.group(0)
        target = lookup.get(source.lower())
        if target is None:  # pragma: no cover - defensive
            return source
        next_char = text[match.end() : match.end() + 1]
        prev_char = text[match.start() - 1 : match.start()]
        return _match_case(source, target, next_char, prev_char)

    return pattern.sub(_replace, text)


# Compiled once at import; the tables are immutable data.
_FOLD = _compile_table(LATIN_FOLD_TABLE)
_FOLD_WITH_C = _compile_table(list(LATIN_FOLD_TABLE) + list(LATIN_FOLD_BARE_C))
_RENDER = {scheme: _compile_table(table) for scheme, table in RENDER_TABLES.items() if table}

# Any leftover apostrophe-like character that is not the tail of a canonical
# oʻ/gʻ is a tutuq belgisi and is unified on U+02BC. The negative lookbehind
# protects the canonical sequences the fold table has just produced.
_STRAY_APOSTROPHE = re.compile(
    "(?<![oOgG])" + re.escape(TURNED_COMMA) + "|"
    "[" + re.escape("".join(a for a in APOSTROPHE_VARIANTS if a != TURNED_COMMA)) + "]"
)


# --------------------------------------------------------------------------
# Stage 1 — Unicode normalization
# --------------------------------------------------------------------------

#: Characters that are visually whitespace but break naive tokenizers.
_WHITESPACE_LIKE = re.compile(
    "[\u00a0"       # NO-BREAK SPACE
    "\u1680"        # OGHAM SPACE MARK
    "\u2000-\u200a"  # EN QUAD .. HAIR SPACE
    "\u202f"        # NARROW NO-BREAK SPACE
    "\u205f"        # MEDIUM MATHEMATICAL SPACE
    "\u3000"        # IDEOGRAPHIC SPACE
    "\t]"
)

#: Zero-width characters that carry no meaning for TTS and confuse matching.
_ZERO_WIDTH = re.compile(
    "[\u200b"   # ZERO WIDTH SPACE
    "\u200c"    # ZERO WIDTH NON-JOINER
    "\u200d"    # ZERO WIDTH JOINER
    "\ufeff"    # ZERO WIDTH NO-BREAK SPACE / BOM
    "\u00ad]"   # SOFT HYPHEN
)


def normalize_unicode(text: str) -> str:
    """Normalize ``text`` to NFC and clean up invisible/duplicate whitespace.

    Steps: strip zero-width characters, map exotic spaces to U+0020, collapse
    runs of spaces, apply NFC composition (so ``o`` + combining acute becomes
    ``ó``), and trim. Line structure is preserved — only horizontal whitespace
    is collapsed.

    >>> normalize_unicode("O\\u2019zbek\\u00a0 tili")
    'O’zbek tili'
    """
    if not text:
        return text

    text = _ZERO_WIDTH.sub("", text)
    text = _WHITESPACE_LIKE.sub(" ", text)

    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


# --------------------------------------------------------------------------
# Stage 2 — Cyrillic transliteration
# --------------------------------------------------------------------------


def _is_cyrillic_letter(char: str) -> bool:
    """True if ``char`` is a Cyrillic letter this module knows."""
    return char in CYRILLIC_ALPHABET


def cyrillic_to_latin(text: str) -> str:
    """Transliterate Uzbek Cyrillic into the internal canonical Latin form.

    Non-Cyrillic characters — Latin letters, digits, punctuation, emoji — pass
    through untouched, so mixed-script input is handled by simply calling this
    on the whole string.

    Context-sensitive rules (all data-driven from :mod:`uztext.mappings`):

    * ``е`` → ``ye`` word-initially, after a vowel, or after ъ/ь; ``e`` after a
      consonant.
    * ``ц`` → ``s`` word-initially, ``ts`` elsewhere.
    * ``ъ`` → ``ʼ`` between letters, dropped at a word edge.
    * ``ь`` → always dropped.

    >>> cyrillic_to_latin("Ўзбекистон")
    'Oʻzbekiston'
    """
    if not text:
        return text

    out: List[str] = []
    for index, char in enumerate(text):
        lower = char.lower()
        if lower not in CYRILLIC_TO_LATIN:
            out.append(char)  # digits, punctuation, Latin, spaces
            continue

        prev = text[index - 1] if index else ""
        nxt = text[index + 1] if index + 1 < len(text) else ""
        prev_lower = prev.lower()

        if lower == "е":
            initial = not _is_cyrillic_letter(prev)
            target = (
                CYRILLIC_E_IOTATED
                if initial or prev_lower in CYRILLIC_VOWELS or prev_lower in CYRILLIC_SIGNS
                else CYRILLIC_E_PLAIN
            )
        elif lower == "ц":
            initial = not _is_cyrillic_letter(prev)
            target = CYRILLIC_TS_INITIAL if initial else CYRILLIC_TS_MEDIAL
        elif lower == "ъ":
            medial = _is_cyrillic_letter(prev) and _is_cyrillic_letter(nxt)
            target = CYRILLIC_HARD_SIGN_MEDIAL if medial else CYRILLIC_HARD_SIGN_EDGE
        else:
            target = CYRILLIC_TO_LATIN[lower]

        out.append(_match_case(char, target, nxt, prev))

    return "".join(out)


# --------------------------------------------------------------------------
# Stage 3 — Latin variant folding
# --------------------------------------------------------------------------


def fold_latin_variants(text: str, *, fold_bare_c: bool = True) -> str:
    """Fold every known Latin spelling variant into the internal canonical form.

    This runs on *all* input, whatever scheme it was written in, because real
    corpora mix orthographies inside a single document (and often a single
    sentence). ``oʻ``, ``o'``, ``o’``, ``o```, ``ó``, ``ö`` and ``ō`` all
    become the same canonical token ``oʻ``.

    Args:
        text: Text that is already Latin (call :func:`cyrillic_to_latin` first
            if it may contain Cyrillic).
        fold_bare_c: Map a standalone ``c`` (not part of ``ch``) to ``ts``.
            ``c`` is not a letter of the 1995 alphabet, so this recovers the
            2019 spelling ``konstituciya`` → ``konstitutsiya``. Set to ``False``
            when the text is known to contain untransliterated foreign words
            such as *Coca-Cola*.

    Returns:
        The canonical-form text.

    >>> fold_latin_variants("Ózbek va O'zbek va Özbek")
    'Oʻzbek va Oʻzbek va Oʻzbek'
    """
    if not text:
        return text

    folded = _apply_table(text, _FOLD_WITH_C if fold_bare_c else _FOLD)
    # Whatever apostrophe-ish character survived is not part of oʻ/gʻ, so it is
    # a tutuq belgisi: unify it on U+02BC.
    return _STRAY_APOSTROPHE.sub(MODIFIER_APOSTROPHE, folded)


# --------------------------------------------------------------------------
# Stage 4 — Rendering
# --------------------------------------------------------------------------


def render(text: str, scheme: LatinScheme = LatinScheme.LATIN_1995) -> str:
    """Render canonical-form ``text`` in the orthography of ``scheme``.

    The input is assumed to be in the internal canonical form (the output of
    :func:`fold_latin_variants`). Characters with no entry in the scheme's
    table — digits, punctuation, foreign words — pass through.

    >>> render("Oʻzbekiston", LatinScheme.LATIN_2026)
    'Ózbekiston'
    >>> render("Oʻzbekiston", LatinScheme.LATIN_1995)
    'Oʻzbekiston'
    """
    if not isinstance(scheme, LatinScheme):
        raise TypeError(f"scheme must be a LatinScheme, got {type(scheme).__name__}")

    compiled = _RENDER.get(scheme)
    if compiled is None:  # LATIN_1995: canonical form, nothing to do.
        return text
    return _apply_table(text, compiled)


# --------------------------------------------------------------------------
# Full pipeline
# --------------------------------------------------------------------------


def normalize(
    text: str,
    output_scheme: LatinScheme = LatinScheme.LATIN_1995,
    *,
    fold_bare_c: bool = True,
) -> str:
    """Normalize Uzbek text of any script/orthography into ``output_scheme``.

    The full front-end pipeline for a TTS system:
    unicode-normalize → transliterate Cyrillic → fold Latin variants to the
    internal canonical form → render the target orthography.

    Args:
        text: Raw input in Cyrillic, any Latin orthography, or a mix of both.
        output_scheme: Orthography to emit. Defaults to
            :attr:`LatinScheme.LATIN_1995`, the current de-facto standard.
        fold_bare_c: See :func:`fold_latin_variants`.

    Returns:
        Normalized text in the requested orthography.

    >>> normalize("Ўзбекистон Республикаси")
    'Oʻzbekiston Respublikasi'
    >>> normalize("Ózbekiston", LatinScheme.LATIN_2026)
    'Ózbekiston'
    """
    text = normalize_unicode(text)
    text = cyrillic_to_latin(text)
    text = fold_latin_variants(text, fold_bare_c=fold_bare_c)
    return render(text, output_scheme)

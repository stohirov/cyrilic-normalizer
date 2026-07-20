"""Table-driven Uzbek text normalizer and Cyrillic-to-Latin transliterator.

The pipeline has four stages, each exposed as a pure function:

1. :func:`normalize_unicode` - NFC plus whitespace cleanup.
2. :func:`cyrillic_to_latin` - Cyrillic to internal canonical Latin
   (a no-op for text that contains no Cyrillic, so mixed-script input works).
3. :func:`fold_latin_variants` - *every* known Latin spelling to the internal
   canonical form.
4. :func:`render` - internal canonical form to the requested orthography.

:func:`normalize` chains all four and is the entry point for the TTS front-end.

The internal canonical form is the 1995 orthography with canonical Unicode
modifier letters; see :mod:`uztext.mappings` for the full definition.

Doctests below spell non-ASCII characters as escapes so that every comment and
docstring in this package stays pure ASCII.

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

    A single-character source is genuinely ambiguous between title case and all
    caps, so the neighbours decide: look right first, and fall back to looking
    left when the match sits at the end of a word.

    ====================  ==========  ==========  ========  ========
    source                prev_char   next_char   target    result
    ====================  ==========  ==========  ========  ========
    s-cedilla, lower      -           -           sh        sh
    S-cedilla             -           a           sh        Sh
    S-cedilla             -           A           sh        SH
    CHE, in an all-caps   capital     -           ch        CH
      word ending in it
    SHA, in "SHA."        -           .           sh        Sh
    SH                    -           -           s-ced.    S-cedilla
    ====================  ==========  ==========  ========  ========

    Caseless characters in ``source`` (for instance the modifier letter U+02BB
    in the canonical o letter) are ignored when deciding the case.
    """
    if not target:
        return target

    title = target[:1].upper() + target[1:].lower()

    cased = [c for c in source if c.isupper() or c.islower()]
    if not cased or all(c.islower() for c in cased):
        return target.lower()

    if all(c.isupper() for c in cased):
        if len(cased) > 1:
            # The whole match was capitals: keep shouting.
            return target.upper()
        # A single capital: title case or all caps? The letter to the right wins.
        if next_char.isupper():
            return target.upper()
        if next_char.islower():
            return title
        # No cased letter to the right (end of an all-caps word, or an
        # abbreviation followed by a full stop): ask the left instead.
        return target.upper() if prev_char.isupper() else title

    # Mixed case, for instance "Sh" or a capital o letter: title case.
    return title


def _compile_table(pairs: Iterable[Tuple[str, str]]) -> Tuple[Pattern[str], Dict[str, str]]:
    """Compile ``(source, target)`` pairs into a longest-match-first regex.

    The lookup dict is keyed on the NFC-normalized, lower-cased source, which is
    what the substitution callback uses after case-folding the match.
    """
    lookup: Dict[str, str] = {}
    for source, target in pairs:
        key = unicodedata.normalize("NFC", source).lower()
        lookup.setdefault(key, target)

    # Longest first, so digraphs and letter-plus-apostrophe sequences beat
    # single characters.
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
# o/g letter is a tutuq belgisi and is unified on U+02BC. The negative
# lookbehind protects the canonical sequences the fold table has just produced.
_STRAY_APOSTROPHE = re.compile(
    "(?<![oOgG])" + re.escape(TURNED_COMMA) + "|"
    "[" + re.escape("".join(a for a in APOSTROPHE_VARIANTS if a != TURNED_COMMA)) + "]"
)


# --------------------------------------------------------------------------
# Stage 1 - Unicode normalization
# --------------------------------------------------------------------------

#: Characters that are visually whitespace but break naive tokenizers.
_WHITESPACE_LIKE = re.compile(
    "[\u00a0"         # NO-BREAK SPACE
    "\u1680"          # OGHAM SPACE MARK
    "\u2000-\u200a"   # EN QUAD .. HAIR SPACE
    "\u202f"          # NARROW NO-BREAK SPACE
    "\u205f"          # MEDIUM MATHEMATICAL SPACE
    "\u3000"          # IDEOGRAPHIC SPACE
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
    """Normalize ``text`` to NFC and clean up invisible or duplicate whitespace.

    Steps: strip zero-width characters, map exotic spaces to U+0020, collapse
    runs of spaces, apply NFC composition (so that a base letter followed by a
    combining accent becomes a single precomposed character), and trim. Line
    structure is preserved - only horizontal whitespace is collapsed.

    >>> normalize_unicode("O\\u2019zbek\\u00a0 tili") == "O\\u2019zbek tili"
    True
    """
    if not text:
        return text

    text = _ZERO_WIDTH.sub("", text)
    text = _WHITESPACE_LIKE.sub(" ", text)

    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


# --------------------------------------------------------------------------
# Stage 2 - Cyrillic transliteration
# --------------------------------------------------------------------------


def _is_cyrillic_letter(char: str) -> bool:
    """True if ``char`` is a Cyrillic letter this module knows."""
    return char in CYRILLIC_ALPHABET


def cyrillic_to_latin(text: str) -> str:
    """Transliterate Uzbek Cyrillic into the internal canonical Latin form.

    Non-Cyrillic characters - Latin letters, digits, punctuation, emoji - pass
    through untouched, so mixed-script input is handled by simply calling this
    on the whole string.

    Context-sensitive rules, all data-driven from :mod:`uztext.mappings`:

    * CYRILLIC IE becomes "ye" word-initially, after a vowel, or after a hard
      or soft sign, and "e" after a consonant.
    * CYRILLIC TSE becomes "s" word-initially and "ts" elsewhere.
    * CYRILLIC HARD SIGN becomes the tutuq belgisi (U+02BC) between letters and
      is dropped at a word edge.
    * CYRILLIC SOFT SIGN is always dropped.

    The doctest below transliterates the Cyrillic spelling of "Uzbekistan".

    >>> name = "\\u040e\\u0437\\u0431\\u0435\\u043a\\u0438\\u0441\\u0442\\u043e\\u043d"
    >>> cyrillic_to_latin(name) == "O\\u02bbzbekiston"
    True
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

        if lower == "е":  # CYRILLIC IE
            initial = not _is_cyrillic_letter(prev)
            target = (
                CYRILLIC_E_IOTATED
                if initial or prev_lower in CYRILLIC_VOWELS or prev_lower in CYRILLIC_SIGNS
                else CYRILLIC_E_PLAIN
            )
        elif lower == "ц":  # CYRILLIC TSE
            initial = not _is_cyrillic_letter(prev)
            target = CYRILLIC_TS_INITIAL if initial else CYRILLIC_TS_MEDIAL
        elif lower == "ъ":  # CYRILLIC HARD SIGN
            medial = _is_cyrillic_letter(prev) and _is_cyrillic_letter(nxt)
            target = CYRILLIC_HARD_SIGN_MEDIAL if medial else CYRILLIC_HARD_SIGN_EDGE
        else:
            target = CYRILLIC_TO_LATIN[lower]

        out.append(_match_case(char, target, nxt, prev))

    return "".join(out)


# --------------------------------------------------------------------------
# Stage 3 - Latin variant folding
# --------------------------------------------------------------------------


def fold_latin_variants(text: str, *, fold_bare_c: bool = True) -> str:
    """Fold every known Latin spelling variant into the internal canonical form.

    This runs on *all* input, whatever scheme it was written in, because real
    corpora mix orthographies inside a single document, and often inside a
    single sentence. The o letter written with a turned comma, an ASCII quote,
    a typographic quote, a backtick, an acute, an umlaut or a macron all become
    the same canonical token.

    Args:
        text: Text that is already Latin (call :func:`cyrillic_to_latin` first
            if it may contain Cyrillic).
        fold_bare_c: Map a standalone "c" (not part of "ch") to "ts". "c" is not
            a letter of the 1995 alphabet, so this recovers the 2019 spelling:
            "konstituciya" becomes "konstitutsiya". Set to ``False`` when the
            text is known to contain untransliterated foreign words such as
            "Coca-Cola".

    Returns:
        The canonical-form text.

    >>> fold_latin_variants("\\u00d3zbek va O'zbek") == "O\\u02bbzbek va O\\u02bbzbek"
    True
    """
    if not text:
        return text

    folded = _apply_table(text, _FOLD_WITH_C if fold_bare_c else _FOLD)
    # Whatever apostrophe-like character survived is not part of the o or g
    # letter, so it is a tutuq belgisi: unify it on U+02BC.
    return _STRAY_APOSTROPHE.sub(MODIFIER_APOSTROPHE, folded)


# --------------------------------------------------------------------------
# Stage 4 - Rendering
# --------------------------------------------------------------------------


def render(text: str, scheme: LatinScheme = LatinScheme.LATIN_1995) -> str:
    """Render canonical-form ``text`` in the orthography of ``scheme``.

    The input is assumed to be in the internal canonical form, that is, the
    output of :func:`fold_latin_variants`. Characters with no entry in the
    scheme's table - digits, punctuation, foreign words - pass through.

    >>> canonical = "O\\u02bbzbekiston"
    >>> render(canonical, LatinScheme.LATIN_2026) == "\\u00d6zbekiston"
    True
    >>> render(canonical, LatinScheme.LATIN_1995) == canonical
    True
    """
    if not isinstance(scheme, LatinScheme):
        raise TypeError(f"scheme must be a LatinScheme, got {type(scheme).__name__}")

    compiled = _RENDER.get(scheme)
    if compiled is None:  # LATIN_1995 is the canonical form: nothing to do.
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
    """Normalize Uzbek text of any script or orthography into ``output_scheme``.

    The full front-end pipeline for a TTS system: unicode-normalize, then
    transliterate Cyrillic, then fold Latin variants into the internal
    canonical form, then render the target orthography.

    Args:
        text: Raw input in Cyrillic, any Latin orthography, or a mix of both.
        output_scheme: Orthography to emit. Defaults to
            :attr:`LatinScheme.LATIN_1995`, the current de-facto standard.
        fold_bare_c: See :func:`fold_latin_variants`.

    Returns:
        Normalized text in the requested orthography.

    >>> normalize("O'zbekiston") == "O\\u02bbzbekiston"
    True
    >>> normalize("O'zbekiston", LatinScheme.LATIN_2026) == "\\u00d6zbekiston"
    True
    """
    text = normalize_unicode(text)
    text = cyrillic_to_latin(text)
    text = fold_latin_variants(text, fold_bare_c=fold_bare_c)
    return render(text, output_scheme)

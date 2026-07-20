"""Data tables for Uzbek text normalization.

This module contains *only data* - no algorithms. The engine in
:mod:`uztext.normalizer` is generic and driven entirely by the tables here.
Adding support for a future orthography reform means adding one entry to
:data:`RENDER_TABLES` (and, if the reform introduces new letter shapes, a few
entries to :data:`LATIN_FOLD_TABLE`); no code changes are required.

Notation used in the comments below
-----------------------------------
All comments are ASCII, so non-ASCII letters are named rather than shown:

    "o + U+02BB"        the 1995 letter written o followed by a turned comma
    "o-acute U+00F3"    2019 letter
    "o-umlaut U+00F6"   1993 and 2026 letter
    "g-breve U+011F"    1993 and 2026 letter
    "g-acute U+01F5"    2019 letter
    "s-cedilla U+015F"  1993 and 2026 letter for the "sh" sound
    "c-cedilla U+00E7"  1993 and 2026 letter for the "ch" sound

Internal canonical form
-----------------------
Everything folds into, and renders from, the **1995 apostrophe orthography with
canonical Unicode modifier letters**:

    o + U+02BB MODIFIER LETTER TURNED COMMA     (the "o-turned-comma" letter)
    g + U+02BB MODIFIER LETTER TURNED COMMA     (the "g-turned-comma" letter)
    sh, ch, ng                                  (digraphs, plain ASCII)
    U+02BC MODIFIER LETTER APOSTROPHE           (tutuq belgisi / glottal stop)

Rationale: it is the current de-facto standard, the overwhelming majority of
existing Uzbek corpora and lexicons use it, it is pure ASCII apart from two
well-defined modifier letters, and it is unambiguous (unlike a plain ASCII
quote, which is used both as the letter tail and as the glottal-stop marker).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------
# Canonical characters
# --------------------------------------------------------------------------

#: U+02BB MODIFIER LETTER TURNED COMMA - the tail of the o- and g- letters.
TURNED_COMMA = "ʻ"

#: U+02BC MODIFIER LETTER APOSTROPHE - tutuq belgisi (glottal stop / separator).
MODIFIER_APOSTROPHE = "ʼ"

#: Canonical spelling of the two apostrophe letters.
CANON_O = "o" + TURNED_COMMA  # o + U+02BB
CANON_G = "g" + TURNED_COMMA  # g + U+02BB


class LatinScheme(Enum):
    """The Uzbek Latin orthographies this module can emit.

    Members are ordered chronologically; the *value* is the year the scheme was
    adopted (or is being phased in), which makes them sortable and readable in
    logs and CLI arguments.
    """

    #: 1993 alphabet - Turkish-style diacritics:
    #: o-umlaut, g-breve, s-cedilla, c-cedilla.
    LATIN_1993 = 1993

    #: 1995 revision - the "o + U+02BB" and "g + U+02BB" letters plus the
    #: digraphs sh, ch, ng. The widely-used current standard and this module's
    #: default output.
    LATIN_1995 = 1995

    #: 2019 draft revision - o-acute and g-acute; "ts" is written "c";
    #: the digraphs sh and ch are kept.
    LATIN_2019 = 2019

    #: 2026 reform - single-character letters replace every digraph:
    #: o-umlaut, g-breve, s-cedilla, c-cedilla. Same letter set as 1993.
    LATIN_2026 = 2026


# --------------------------------------------------------------------------
# Apostrophe-like characters
# --------------------------------------------------------------------------
# Real-world Uzbek text uses a zoo of characters both for the tail of the o/g
# letters and for the tutuq belgisi: ASCII quotes, typographic quotes,
# backticks, primes, acute accents, and the two "correct" modifier letters.
# Every one of them is folded away.

APOSTROPHE_VARIANTS: Tuple[str, ...] = (
    "ʻ",  # MODIFIER LETTER TURNED COMMA - canonical o/g tail
    "ʼ",  # MODIFIER LETTER APOSTROPHE - canonical tutuq belgisi
    "‘",  # LEFT SINGLE QUOTATION MARK - most common typographic mistake
    "’",  # RIGHT SINGLE QUOTATION MARK - word processor autocorrect
    "'",  # APOSTROPHE - plain ASCII typewriter quote
    "`",  # GRAVE ACCENT - "o + backtick", common on phone keyboards
    "´",  # ACUTE ACCENT - mistyped standalone accent
    "ʹ",  # MODIFIER LETTER PRIME
    "ʽ",  # MODIFIER LETTER REVERSED COMMA
    "′",  # PRIME - copied from typeset material
    "‛",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
)

# --------------------------------------------------------------------------
# Latin input folding: every known representation -> internal canonical form
# --------------------------------------------------------------------------
# Order does not matter here; the engine sorts by descending length so that
# digraphs and two-character sequences always win over single characters.
# All sources are NFC-normalized and lower-cased by the engine, which matches
# case-insensitively and restores the original casing.

LATIN_FOLD_TABLE: List[Tuple[str, str]] = [
    # -- the o letter -----------------------------------------------------
    *[("o" + a, CANON_O) for a in APOSTROPHE_VARIANTS],  # o + any apostrophe
    ("ó", CANON_O),  # o-acute U+00F3: 2019
    ("ö", CANON_O),  # o-umlaut U+00F6: 1993 and 2026
    ("ō", CANON_O),  # o-macron U+014D: seen in 2021 reform drafts
    ("ô", CANON_O),  # o-circumflex U+00F4: ad-hoc transliteration
    ("ò", CANON_O),  # o-grave U+00F2: ad-hoc, OCR confusion with o-acute
    ("õ", CANON_O),  # o-tilde U+00F5: ad-hoc
    ("ŏ", CANON_O),  # o-breve U+014F: ad-hoc, mirrors the Cyrillic letter
    ("ǒ", CANON_O),  # o-caron U+01D2: ad-hoc
    # -- the g letter -----------------------------------------------------
    *[("g" + a, CANON_G) for a in APOSTROPHE_VARIANTS],  # g + any apostrophe
    ("ğ", CANON_G),  # g-breve U+011F: 1993 and 2026
    ("ǵ", CANON_G),  # g-acute U+01F5: 2019
    ("ḡ", CANON_G),  # g-macron U+1E21: seen in 2021 reform drafts
    ("ĝ", CANON_G),  # g-circumflex U+011D: ad-hoc
    ("ġ", CANON_G),  # g-dot-above U+0121: ad-hoc
    ("ǧ", CANON_G),  # g-caron U+01E7: ad-hoc
    ("g̀", CANON_G),  # g + combining grave U+0300: OCR artefact
    # -- the sh sound -----------------------------------------------------
    ("sh", "sh"),  # canonical digraph; listed so it wins over shorter matches
    ("ş", "sh"),  # s-cedilla U+015F: 1993 and 2026
    ("ș", "sh"),  # s-comma-below U+0219: Romanian lookalike, mojibake
    ("š", "sh"),  # s-caron U+0161: Slavic-style transliteration
    ("ŝ", "sh"),  # s-circumflex U+015D: ad-hoc
    # -- the ch sound -----------------------------------------------------
    ("ch", "ch"),  # canonical digraph
    ("ç", "ch"),  # c-cedilla U+00E7: 1993 and 2026
    ("č", "ch"),  # c-caron U+010D: Slavic-style transliteration
    ("ć", "ch"),  # c-acute U+0107: ad-hoc
    ("ĉ", "ch"),  # c-circumflex U+0109: ad-hoc
    # -- the ng sound -----------------------------------------------------
    ("ng", "ng"),  # canonical digraph; unchanged by every scheme so far
    ("ŋ", "ng"),  # eng U+014B: occasionally used in phonetic corpora
]

#: Bare "c" -> "ts". Only applied when ``fold_bare_c=True`` (the default),
#: because "c" is not a letter of the 1995 alphabet: a standalone "c" in Uzbek
#: text is almost always the 2019 spelling of the ts sound
#: ("konstituciya" -> "konstitutsiya"). See README.md for the trade-off with
#: foreign words such as "Coca-Cola".
LATIN_FOLD_BARE_C: List[Tuple[str, str]] = [
    ("c", "ts"),  # c -> ts; "ch" is matched first and therefore protected
]

# --------------------------------------------------------------------------
# Output rendering: internal canonical form -> target orthography
# --------------------------------------------------------------------------
# Each table maps canonical sequences to the target scheme's spelling. Entries
# are applied longest-match-first by the engine. An empty table means the
# scheme *is* the canonical form.

RENDER_TABLES: Dict[LatinScheme, List[Tuple[str, str]]] = {
    # 1993: Turkish-style diacritics for all four sounds.
    LatinScheme.LATIN_1993: [
        (CANON_O, "ö"),  # o + U+02BB -> o-umlaut U+00F6
        (CANON_G, "ğ"),  # g + U+02BB -> g-breve U+011F
        ("sh", "ş"),  # sh -> s-cedilla U+015F
        ("ch", "ç"),  # ch -> c-cedilla U+00E7
        # ng and ts are unchanged
    ],
    # 1995: the canonical form itself - nothing to do.
    LatinScheme.LATIN_1995: [],
    # 2019: acute accents, digraphs sh/ch kept, ts collapses to c.
    LatinScheme.LATIN_2019: [
        (CANON_O, "ó"),  # o + U+02BB -> o-acute U+00F3
        (CANON_G, "ǵ"),  # g + U+02BB -> g-acute U+01F5
        ("ts", "c"),  # ts -> c ("konstitutsiya" -> "konstituciya")
        # sh, ch and ng are unchanged
    ],
    # 2026: one character per sound; the 1993 letter set.
    LatinScheme.LATIN_2026: [
        (CANON_O, "ö"),  # o + U+02BB -> o-umlaut U+00F6. Swap to o-acute
        #   U+00F3 here if the final decree settles on the acute instead.
        (CANON_G, "ğ"),  # g + U+02BB -> g-breve U+011F
        ("sh", "ş"),  # sh -> s-cedilla U+015F
        ("ch", "ç"),  # ch -> c-cedilla U+00E7
        # ng unchanged; ts stays "ts" - the 2026 reform does not adopt 2019's c
    ],
}

# --------------------------------------------------------------------------
# Cyrillic -> canonical Latin
# --------------------------------------------------------------------------
# Context-free single-character mappings, keyed by the lower-case Cyrillic
# letter. Context-sensitive letters (IE, TSE, hard sign, soft sign) are handled
# by the rules below and are deliberately absent from this table.

CYRILLIC_TO_LATIN: Dict[str, str] = {
    "а": "a",  # CYRILLIC A -> a
    "б": "b",  # CYRILLIC BE -> b
    "в": "v",  # CYRILLIC VE -> v
    "г": "g",  # CYRILLIC GHE -> g
    "д": "d",  # CYRILLIC DE -> d
    "ё": "yo",  # CYRILLIC IO -> yo (always iotated in Uzbek)
    "ж": "j",  # CYRILLIC ZHE -> j (Uzbek zhe is /dzh/, not Russian /zh/)
    "з": "z",  # CYRILLIC ZE -> z
    "и": "i",  # CYRILLIC I -> i
    "й": "y",  # CYRILLIC SHORT I -> y
    "к": "k",  # CYRILLIC KA -> k
    "л": "l",  # CYRILLIC EL -> l
    "м": "m",  # CYRILLIC EM -> m
    "н": "n",  # CYRILLIC EN -> n
    "о": "o",  # CYRILLIC O -> o
    "п": "p",  # CYRILLIC PE -> p
    "р": "r",  # CYRILLIC ER -> r
    "с": "s",  # CYRILLIC ES -> s
    "т": "t",  # CYRILLIC TE -> t
    "у": "u",  # CYRILLIC U -> u
    "ф": "f",  # CYRILLIC EF -> f
    "х": "x",  # CYRILLIC HA -> x (velar fricative; distinct from HA
    #                 WITH DESCENDER below)
    "ч": "ch",  # CYRILLIC CHE -> ch
    "ш": "sh",  # CYRILLIC SHA -> sh
    "щ": "shch",  # CYRILLIC SHCHA -> shch (Russian loanwords only)
    "ы": "i",  # CYRILLIC YERU -> i (Uzbek has no such vowel; merges to i)
    "э": "e",  # CYRILLIC E -> e (never iotated)
    "ю": "yu",  # CYRILLIC YU -> yu
    "я": "ya",  # CYRILLIC YA -> ya
    # Uzbek-specific letters
    "ў": CANON_O,  # CYRILLIC SHORT U -> o + U+02BB
    "қ": "q",  # CYRILLIC KA WITH DESCENDER -> q
    "ғ": CANON_G,  # CYRILLIC GHE WITH STROKE -> g + U+02BB
    "ҳ": "h",  # CYRILLIC HA WITH DESCENDER -> h (distinct from HA)
    # Russian-only letters that occur in loanwords and proper nouns
    "ц": "ts",  # CYRILLIC TSE -> ts (overridden word-initially, see below)
    "е": "e",  # CYRILLIC IE -> e (overridden after vowels/signs, below)
    "ъ": MODIFIER_APOSTROPHE,  # CYRILLIC HARD SIGN (overridden at word edges)
    "ь": "",  # CYRILLIC SOFT SIGN -> deleted; no Latin counterpart
}

#: Cyrillic vowels. After one of these, CYRILLIC IE is iotated ("ye").
CYRILLIC_VOWELS = frozenset("аеёиоуўэюяы")

#: Cyrillic separator signs. After one of these, CYRILLIC IE is iotated.
CYRILLIC_SIGNS = frozenset("ъь")

#: CYRILLIC IE renders as this at the start of a word, after a vowel, or after
#: a hard/soft sign. Examples: "Yer", "oyeva", "ob" + tutuq belgisi + "yekt".
CYRILLIC_E_IOTATED = "ye"

#: CYRILLIC IE renders as this after a consonant. Example: "men".
CYRILLIC_E_PLAIN = "e"

#: CYRILLIC TSE renders as this at the start of a word. Example: "sirk".
CYRILLIC_TS_INITIAL = "s"

#: CYRILLIC TSE renders as this elsewhere. Example: "konstitutsiya".
CYRILLIC_TS_MEDIAL = "ts"

#: CYRILLIC HARD SIGN renders as the tutuq belgisi between two letters
#: (a glottal stop, as in "ma" + tutuq belgisi + "no") and as nothing at a word
#: edge, where it carries no sound.
CYRILLIC_HARD_SIGN_MEDIAL = MODIFIER_APOSTROPHE
CYRILLIC_HARD_SIGN_EDGE = ""

#: Every Cyrillic character this module knows about, in both cases.
CYRILLIC_ALPHABET = frozenset(
    list(CYRILLIC_TO_LATIN) + [c.upper() for c in CYRILLIC_TO_LATIN]
)

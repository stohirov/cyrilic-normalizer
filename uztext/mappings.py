"""Data tables for Uzbek text normalization.

This module contains *only data* — no algorithms. The engine in
:mod:`uztext.normalizer` is generic and driven entirely by the tables here.
Adding support for a future orthography reform means adding one entry to
:data:`RENDER_TABLES` (and, if the reform introduces new letter shapes, a few
entries to :data:`LATIN_FOLD_TABLE`); no code changes are required.

Internal canonical form
-----------------------
Everything folds into, and renders from, the **1995 apostrophe orthography with
canonical Unicode modifier letters**:

    oʻ  = "o" + U+02BB MODIFIER LETTER TURNED COMMA
    gʻ  = "g" + U+02BB MODIFIER LETTER TURNED COMMA
    sh, ch, ng                      (digraphs, plain ASCII)
    ʼ   = U+02BC MODIFIER LETTER APOSTROPHE  (tutuq belgisi / glottal stop)

Rationale: it is the current de-facto standard, the overwhelming majority of
existing Uzbek corpora and lexicons use it, it is pure-ASCII apart from two
well-defined modifier letters, and it is unambiguous (unlike ``o'`` with a
typewriter quote, which collides with the glottal-stop marker).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------
# Canonical characters
# --------------------------------------------------------------------------

#: U+02BB MODIFIER LETTER TURNED COMMA — the "tail" of oʻ and gʻ.
TURNED_COMMA = "ʻ"

#: U+02BC MODIFIER LETTER APOSTROPHE — tutuq belgisi (glottal stop / separator).
MODIFIER_APOSTROPHE = "ʼ"

#: Canonical spelling of the two apostrophe letters.
CANON_O = "o" + TURNED_COMMA  # oʻ
CANON_G = "g" + TURNED_COMMA  # gʻ


class LatinScheme(Enum):
    """The Uzbek Latin orthographies this module can emit.

    Members are ordered chronologically; the *value* is the year the scheme was
    adopted (or is being phased in), which makes them sortable and readable in
    logs and CLI arguments.
    """

    #: 1993 alphabet — Turkish-style diacritics: ö ğ ş ç.
    LATIN_1993 = 1993

    #: 1995 revision — apostrophe forms oʻ gʻ and digraphs sh ch ng.
    #: The widely-used current standard and this module's default output.
    LATIN_1995 = 1995

    #: 2019 draft revision — oʻ→ó, gʻ→ǵ, ts→c; digraphs sh/ch kept.
    LATIN_2019 = 2019

    #: 2026 reform — single-character letters replace every digraph:
    #: oʻ→ó, gʻ→ğ, sh→ş, ch→ç.
    LATIN_2026 = 2026


# --------------------------------------------------------------------------
# Apostrophe-like characters
# --------------------------------------------------------------------------
# Real-world Uzbek text uses a zoo of characters for both the oʻ/gʻ tail and
# the tutuq belgisi: ASCII quotes, typographic quotes, backticks, primes,
# acute accents, and the two "correct" modifier letters. Every one of them is
# folded away.

APOSTROPHE_VARIANTS: Tuple[str, ...] = (
    "ʻ",  # ʻ MODIFIER LETTER TURNED COMMA — canonical oʻ/gʻ tail
    "ʼ",  # ʼ MODIFIER LETTER APOSTROPHE — canonical tutuq belgisi
    "‘",  # ‘ LEFT SINGLE QUOTATION MARK — most common typographic mistake
    "’",  # ’ RIGHT SINGLE QUOTATION MARK — Word autocorrect output
    "'",  # ' APOSTROPHE — plain ASCII typewriter quote
    "`",  # ` GRAVE ACCENT — "o+backtick", common on phone keyboards
    "´",  # ´ ACUTE ACCENT — mistyped standalone accent
    "ʹ",  # ʹ MODIFIER LETTER PRIME
    "ʽ",  # ʽ MODIFIER LETTER REVERSED COMMA
    "′",  # ′ PRIME — copied from typeset material
    "‛",  # ‛ SINGLE HIGH-REVERSED-9 QUOTATION MARK
)

# --------------------------------------------------------------------------
# Latin input folding: every known representation -> internal canonical form
# --------------------------------------------------------------------------
# Order does not matter here; the engine sorts by descending length so that
# digraphs and two-character sequences always win over single characters.
# All strings are NFC-normalized lowercase; the engine matches case-insensitively
# and restores the original casing.

LATIN_FOLD_TABLE: List[Tuple[str, str]] = [
    # -- oʻ ---------------------------------------------------------------
    *[("o" + a, CANON_O) for a in APOSTROPHE_VARIANTS],  # o + any apostrophe
    ("ó", CANON_O),  # ó  2019/2026 acute — official post-2019 letter
    ("ö", CANON_O),  # ö  1993 umlaut
    ("ō", CANON_O),  # ō  macron, seen in 2021 reform drafts
    ("ô", CANON_O),  # ô  circumflex, ad-hoc transliteration
    ("ò", CANON_O),  # ò  grave, ad-hoc/OCR confusion with ó
    ("õ", CANON_O),  # õ  tilde, ad-hoc
    ("ŏ", CANON_O),  # ŏ  breve, ad-hoc (mirrors Cyrillic ў breve)
    ("ǒ", CANON_O),  # ǒ  caron, ad-hoc
    # -- gʻ ---------------------------------------------------------------
    *[("g" + a, CANON_G) for a in APOSTROPHE_VARIANTS],  # g + any apostrophe
    ("ğ", CANON_G),  # ğ  1993 and 2026 breve
    ("\u01F5", CANON_G),  # ǵ  2019 acute (U+01F5, precomposed by NFC)
    ("ḡ", CANON_G),  # ḡ  macron, seen in 2021 reform drafts
    ("ĝ", CANON_G),  # ĝ  circumflex, ad-hoc
    ("ġ", CANON_G),  # ġ  dot above, ad-hoc
    ("ǧ", CANON_G),  # ǧ  caron, ad-hoc
    ("g̀", CANON_G),  # g̀  combining grave, OCR artefact
    # -- sh ---------------------------------------------------------------
    ("sh", "sh"),  # canonical digraph — listed so it beats bare "s"/"h" rules
    ("ş", "sh"),  # ş  1993 and 2026 cedilla
    ("ș", "sh"),  # ș  comma-below (Romanian lookalike, common mojibake)
    ("š", "sh"),  # š  caron, Slavic-style transliteration
    ("ŝ", "sh"),  # ŝ  circumflex, ad-hoc
    # -- ch ---------------------------------------------------------------
    ("ch", "ch"),  # canonical digraph
    ("ç", "ch"),  # ç  1993 and 2026 cedilla
    ("č", "ch"),  # č  caron, Slavic-style transliteration
    ("ć", "ch"),  # ć  acute, ad-hoc
    ("ĉ", "ch"),  # ĉ  circumflex, ad-hoc
    # -- ng ---------------------------------------------------------------
    ("ng", "ng"),  # canonical digraph (unchanged by every scheme so far)
    ("ŋ", "ng"),  # ŋ  eng, occasionally used in phonetic corpora
]


#: Bare ``c`` -> ``ts``. Only applied when ``fold_bare_c=True`` (the default),
#: because ``c`` is not a letter of the 1995 alphabet: a standalone ``c`` in
#: Uzbek text is almost always the 2019 spelling of the /ts/ sound
#: (``konstituciya`` -> ``konstitutsiya``). See README for the trade-off with
#: foreign words such as "Coca-Cola".
LATIN_FOLD_BARE_C: List[Tuple[str, str]] = [
    ("c", "ts"),  # c -> ts  (2019 scheme; "ch" is matched first and protected)
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
        (CANON_O, "ö"),  # oʻ -> ö
        (CANON_G, "ğ"),  # gʻ -> ğ
        ("sh", "ş"),  # sh -> ş
        ("ch", "ç"),  # ch -> ç
        # ng, ts unchanged
    ],
    # 1995: the canonical form itself — nothing to do.
    LatinScheme.LATIN_1995: [],
    # 2019: acute accents, digraphs sh/ch kept, ts collapses to c.
    LatinScheme.LATIN_2019: [
        (CANON_O, "ó"),  # oʻ -> ó
        (CANON_G, "\u01F5"),  # gʻ -> ǵ  (U+01F5 latin small letter g with acute)
        ("ts", "c"),  # ts -> c   (konstitutsiya -> konstituciya)
        # sh, ch, ng unchanged
    ],
    # 2026: one character per sound. Keeps 2019's ó, adopts 1993's ğ ş ç.
    LatinScheme.LATIN_2026: [
        (CANON_O, "ó"),  # oʻ -> ó   (official choice; swap to "ö" here
        #             if the final decree settles on the umlaut)
        (CANON_G, "ğ"),  # gʻ -> ğ
        ("sh", "ş"),  # sh -> ş
        ("ch", "ç"),  # ch -> ç
        # ng unchanged; ts kept as ts (the 2026 reform does not adopt 2019's c)
    ],
}

# --------------------------------------------------------------------------
# Cyrillic -> canonical Latin
# --------------------------------------------------------------------------
# Context-free single-character mappings. Context-sensitive letters (е, ц, ъ, ь)
# are handled by the rules below and are deliberately absent from this table.

CYRILLIC_TO_LATIN: Dict[str, str] = {
    "а": "a",  # а -> a
    "б": "b",  # б -> b
    "в": "v",  # в -> v
    "г": "g",  # г -> g
    "д": "d",  # д -> d
    "ё": "yo",  # ё -> yo  (always iotated in Uzbek)
    "ж": "j",  # ж -> j   (Uzbek ж is /dʒ/, not Russian /ʒ/)
    "з": "z",  # з -> z
    "и": "i",  # и -> i
    "й": "y",  # й -> y
    "к": "k",  # к -> k
    "л": "l",  # л -> l
    "м": "m",  # м -> m
    "н": "n",  # н -> n
    "о": "o",  # о -> o
    "п": "p",  # п -> p
    "р": "r",  # р -> r
    "с": "s",  # с -> s
    "т": "t",  # т -> t
    "у": "u",  # у -> u
    "ф": "f",  # ф -> f
    "х": "x",  # х -> x   (velar fricative; distinct from ҳ)
    "ч": "ch",  # ч -> ch
    "ш": "sh",  # ш -> sh
    "щ": "shch",  # щ -> shch (Russian loanwords only)
    "ы": "i",  # ы -> i   (Uzbek has no /ɨ/; merges with i)
    "э": "e",  # э -> e   (never iotated)
    "ю": "yu",  # ю -> yu
    "я": "ya",  # я -> ya
    # Uzbek-specific letters
    "ў": CANON_O,  # ў -> oʻ
    "қ": "q",  # қ -> q
    "ғ": CANON_G,  # ғ -> gʻ
    "ҳ": "h",  # ҳ -> h   (glottal/pharyngeal; distinct from х)
    # Russian-only letters that occur in loanwords and proper nouns
    "ц": "ts",  # ц -> ts  (overridden word-initially, see CYRILLIC_TS_*)
    "е": "e",  # е -> e   (overridden after vowels/signs, see below)
    "ъ": MODIFIER_APOSTROPHE,  # ъ -> ʼ (overridden at word edges)
    "ь": "",  # ь -> deleted (soft sign has no Latin counterpart)
}

#: Cyrillic vowels — after one of these, ``е`` is iotated (``ye``).
CYRILLIC_VOWELS = frozenset("аеёиоуўэюяы")

#: Cyrillic separator signs — after one of these, ``е`` is iotated (``ye``).
CYRILLIC_SIGNS = frozenset("ъь")

#: ``е`` renders as this at the start of a word, after a vowel, or after ъ/ь.
CYRILLIC_E_IOTATED = "ye"  # Ер -> Yer, оева -> oyeva, объект -> obʼyekt

#: ``е`` renders as this after a consonant.
CYRILLIC_E_PLAIN = "e"  # мен -> men

#: ``ц`` renders as this at the start of a word.
CYRILLIC_TS_INITIAL = "s"  # цирк -> sirk

#: ``ц`` renders as this elsewhere.
CYRILLIC_TS_MEDIAL = "ts"  # конституция -> konstitutsiya

#: ``ъ`` renders as this between two letters (glottal stop), and as "" at a
#: word boundary where it carries no sound.
CYRILLIC_HARD_SIGN_MEDIAL = MODIFIER_APOSTROPHE  # маъно -> maʼno
CYRILLIC_HARD_SIGN_EDGE = ""  # съезд-final ъ -> dropped

#: Every Cyrillic character this module knows about (both cases).
CYRILLIC_ALPHABET = frozenset(
    list(CYRILLIC_TO_LATIN) + [c.upper() for c in CYRILLIC_TO_LATIN]
)

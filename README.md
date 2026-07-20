# uztext - Uzbek text normalization for TTS front-ends

Normalizes real-world Uzbek text - Cyrillic, any of the four Latin
orthographies, or a mix of all of them inside one sentence - into a single,
selectable output orthography.

```python
from uztext import normalize, LatinScheme

normalize("O'zbekiston Respublikasi")           # 1995: o + U+02BB
normalize("Ozbekiston", LatinScheme.LATIN_2026) # 2026: o-umlaut
```

## Notation in this document

Every file in this project keeps its comments, docstrings and documentation in
pure ASCII, so Uzbek letters are named rather than shown:

| Name used here | Codepoint | Used by |
|---|---|---|
| `o + U+02BB` | `o` + MODIFIER LETTER TURNED COMMA | 1995 |
| `g + U+02BB` | `g` + MODIFIER LETTER TURNED COMMA | 1995 |
| `o-acute` | U+00F3 | 2019 |
| `g-acute` | U+01F5 | 2019 |
| `o-umlaut` | U+00F6 | 1993, 2026 |
| `g-breve` | U+011F | 1993, 2026 |
| `s-cedilla` | U+015F | 1993, 2026 |
| `c-cedilla` | U+00E7 | 1993, 2026 |
| `tutuq belgisi` | U+02BC MODIFIER LETTER APOSTROPHE | all schemes |

The actual characters appear only in code, in data tables and in test
fixtures - never in prose.

## The four orthographies

| Sound | 1993 | **1995 (default)** | 2019 | 2026 |
|---|---|---|---|---|
| the "o" vowel | `o-umlaut` | **`o + U+02BB`** | `o-acute` | `o-umlaut` |
| the "g" consonant | `g-breve` | **`g + U+02BB`** | `g-acute` | `g-breve` |
| "sh" | `s-cedilla` | **`sh`** | `sh` | `s-cedilla` |
| "ch" | `c-cedilla` | **`ch`** | `ch` | `c-cedilla` |
| "ng" | `ng` | **`ng`** | `ng` | `ng` |
| "ts" | `ts` | **`ts`** | `c` | `ts` |
| glottal stop | `tutuq belgisi` | **`tutuq belgisi`** | `tutuq belgisi` | `tutuq belgisi` |

* **1993** - the first post-Soviet Latin alphabet, Turkish-style diacritics.
  Short-lived, but it survives in older printed material and in scanned corpora.
* **1995** - replaced the diacritics with apostrophe forms and digraphs. This is
  the current de-facto standard and the **default output**: essentially all
  existing Uzbek corpora, lexicons, dictionaries and grapheme-to-phoneme
  resources use it, so emitting it keeps a TTS front-end compatible with
  everything downstream.
* **2019** - draft revision: acute accents for the o and g letters, and "ts"
  written "c". It kept the "sh" and "ch" digraphs.
* **2026** - the current reform: one character per sound, ending digraphs
  entirely. Its letter set is the 1993 one, so the two schemes render
  identically today. They are kept separate because they are separate decrees
  and only one of them is a live migration target; a later divergence is then a
  table edit rather than a refactor.

> **The 2026 reform is being phased in gradually.** Signage, textbooks, official
> documents and web content will be migrating for years, and a large body of
> 1995 text will simply never be converted. Mixed-orthography input is not an
> edge case - it is the normal case, and will stay that way. That is why the
> folding step is unconditional.

If the final decree settles on `o-acute` rather than `o-umlaut`, change exactly
one line: the `LATIN_2026` entry in `uztext/mappings.py`.

## Two independent axes

The module deliberately keeps **input folding** and **output rendering**
separate. They are not inverses of each other and they change for different
reasons: folding grows when you discover a new way people spell things,
rendering grows when a government adopts a new alphabet.

```
raw text
   |
   +- normalize_unicode()     NFC, strip zero-width, unify spaces
   |
   +- cyrillic_to_latin()     Cyrillic -> canonical  (no-op if no Cyrillic)
   |
   +- fold_latin_variants()   ALL Latin spellings -> canonical  <- always runs
   |
   +- render(scheme)          canonical -> target orthography
```

### Input folding - accept everything

`fold_latin_variants` recognizes every known written representation of each
sound and collapses it onto one internal token. For the o letter alone that
includes the canonical form, plus `o` followed by any of eleven apostrophe-like
characters (ASCII quote, both typographic quotes, backtick, acute accent,
prime, and the modifier letters), plus o-acute, o-umlaut, o-macron,
o-circumflex, o-grave, o-tilde, o-breve and o-caron. This runs on *every*
input, regardless of which scheme it claims to be in, because a single document
- often a single sentence - mixes several.

### Output rendering - emit one

`render` goes the other way, from the canonical form to exactly one
orthography. Adding a fifth scheme means adding an enum member and a table to
`RENDER_TABLES`; no code changes.

## Internal canonical form

**The 1995 orthography with canonical Unicode modifier letters.**

| | codepoint |
|---|---|
| tail of the o and g letters | U+02BB MODIFIER LETTER TURNED COMMA |
| tutuq belgisi | U+02BC MODIFIER LETTER APOSTROPHE |
| `sh`, `ch`, `ng` | plain ASCII digraphs |

Why 1995: it is what the existing data uses, it is unambiguous (unlike the
ASCII quote, which serves both as the letter tail and as the glottal stop), and
it is stable - the two modifier letters have well-defined Unicode identities, so
normalized text compares equal byte for byte.

## Convention decisions

Every judgement call is listed here, and each is a one-line change in
`mappings.py` if your corpus disagrees.

### CYRILLIC TSE (the "ts" sound)

* **Word-initial becomes `s`**: "sirk". This matches the official rules and
  Uzbek phonotactics, which has no initial "ts" cluster.
* **Elsewhere it becomes `ts`**: "konstitutsiya".
* **Rendering**: only `LATIN_2019` writes it `c` ("konstituciya").
* **Folding a bare `c`**: `c` is not a letter of the 1995 alphabet, so a
  standalone `c` (not part of `ch`) is folded to `ts` by default - this is what
  makes 2019-spelled input round-trip. The cost is foreign words:
  "Coca-Cola" becomes "Tsotsa-Tsola". Pass `fold_bare_c=False` when the input is
  known to contain untransliterated foreign names. For a TTS pipeline the
  default is usually right: a `c` reaching the phonemizer unmapped is worse than
  an over-eager `ts`.

### CYRILLIC IE ("e" / "ye")

* **`ye`** word-initially, after a vowel, or after a hard or soft sign:
  "Yer", "Yevropa", "oyeva", "ob" + tutuq belgisi + "yekt".
* **`e`** after a consonant: "men".
* **CYRILLIC E becomes `e`** always - it is never iotated, which is exactly what
  distinguishes it from CYRILLIC IE.
* CYRILLIC IO, YU and YA are always iotated: `yo`, `yu`, `ya`.

### Soft sign and hard sign

* **Soft sign: deleted.** It marks palatalization, which Uzbek Latin does not
  write: "medal", "Olga". Its one visible effect is triggering the iotated `ye`.
* **Hard sign between letters: the tutuq belgisi (U+02BC).** It is a real
  glottal stop and vowel-length marker that TTS must see: "ma" + tutuq belgisi +
  "no", "san" + tutuq belgisi + "at".
* **Hard sign at a word edge: deleted**, where it carries no sound.
* All apostrophe-like characters that are *not* the tail of the o or g letter
  are unified on U+02BC.

### 2026 letter choices

* `o-umlaut` for the o vowel - the 1993 letter, not 2019's `o-acute`.
* `g-breve`, `s-cedilla`, `c-cedilla` - also carried over from 1993.
* `ng` unchanged - no reform has touched it.
* `ts` unchanged - the 2026 reform does **not** adopt 2019's `c`.

### Other

* **CYRILLIC HA becomes `x`, CYRILLIC HA WITH DESCENDER becomes `h`** - kept
  distinct; merging them would lose a phonemic contrast the TTS voice may
  render differently.
* **CYRILLIC ZHE becomes `j`** - the Uzbek letter is an affricate, not the
  Russian fricative.
* **CYRILLIC YERU becomes `i`**, **CYRILLIC SHCHA becomes `shch`** - Russian
  loanwords only.
* **Casing** is preserved through multi-character mappings. A single capital is
  ambiguous between title case and all caps, so the neighbours decide: the
  letter to the right wins ("Shahar" versus "SHAHAR"), and when there is none,
  the letter to the left does - a final capital inside an all-caps word stays
  all caps, while a single-letter abbreviation followed by a full stop is
  title-cased.
* **Digits, punctuation, whitespace and foreign words pass through** untouched.
* **`sh` and `ch` are always read as digraphs.** An `s` followed by an `h`
  across a morpheme boundary would be misread, but in practice such words are
  spelled with an explicit tutuq belgisi, which the digraph rule does not touch.

## Known limitations

* An ASCII `o'` is genuinely ambiguous between the o letter and `o` followed by
  a glottal stop. It is always folded to the o letter, which is right in the
  overwhelming majority of words.
* A morpheme-boundary `ts` becomes `c` under `LATIN_2019` rendering. This
  affects 2019 output only; the default 1995 output is unaffected.

## API

```python
class LatinScheme(Enum):      # LATIN_1993 | LATIN_1995 | LATIN_2019 | LATIN_2026

normalize_unicode(text)                        -> str
cyrillic_to_latin(text)                        -> str
fold_latin_variants(text, *, fold_bare_c=True) -> str
render(text, scheme=LatinScheme.LATIN_1995)    -> str
normalize(text, output_scheme=LatinScheme.LATIN_1995, *, fold_bare_c=True) -> str
```

All functions are pure: no globals are mutated, the input string is never
modified, and the same input always yields the same output.

## Tests

```bash
python -m pytest tests --doctest-modules uztext
```

# uztext — Uzbek text normalization for TTS front-ends

Normalizes real-world Uzbek text — Cyrillic, any of the four Latin
orthographies, or a mix of all of them inside one sentence — into a single,
selectable output orthography.

```python
from uztext import normalize, LatinScheme

normalize("Ўзбекистон Республикаси")          # 'Oʻzbekiston Respublikasi'
normalize("Ózbekiston")                        # 'Oʻzbekiston'
normalize("o'zbek", LatinScheme.LATIN_2026)    # 'ózbek'
```

## The four orthographies

| Sound | 1993 | **1995 (default)** | 2019 | 2026 | Cyrillic |
|---|---|---|---|---|---|
| /oʻ/ | `ö` | **`oʻ`** | `ó` | `ó` | `ў` |
| /gʻ/ | `ğ` | **`gʻ`** | `ǵ` | `ğ` | `ғ` |
| /ʃ/ | `ş` | **`sh`** | `sh` | `ş` | `ш` |
| /tʃ/ | `ç` | **`ch`** | `ch` | `ç` | `ч` |
| /ŋ/ | `ng` | **`ng`** | `ng` | `ng` | `нг` |
| /ts/ | `ts` | **`ts`** | `c` | `ts` | `ц` |
| glottal stop | `ʼ` | **`ʼ`** | `ʼ` | `ʼ` | `ъ` |

* **1993** — the first post-Soviet Latin alphabet, Turkish-style diacritics.
  Short-lived, but it survives in older printed material and in scanned corpora.
* **1995** — replaced the diacritics with apostrophe forms and digraphs. This is
  the current de-facto standard and the **default output**: essentially all
  existing Uzbek corpora, lexicons, dictionaries and G2P resources use it, so
  emitting it keeps a TTS front-end compatible with everything downstream.
* **2019** — draft revision: acute accents for `oʻ`/`gʻ`, and `ts` written `c`.
  It kept the `sh`/`ch` digraphs.
* **2026** — the current reform: one character per sound, ending digraphs
  entirely. It keeps 2019's `ó` and adopts 1993's `ğ ş ç`.

> **The 2026 reform is being phased in gradually.** Signage, textbooks, official
> documents and web content will be migrating for years, and a large body of
> 1995 text will simply never be converted. Mixed-orthography input is not an
> edge case — it is the normal case, and will stay that way. That is why the
> folding step is unconditional.

If the final decree settles on `ö` rather than `ó` for /oʻ/, change exactly one
line: the `LATIN_2026` entry in `uztext/mappings.py`.

## Two independent axes

The module deliberately keeps **input folding** and **output rendering**
separate. They are not inverses of each other and they change for different
reasons: folding grows when you discover a new way people spell things,
rendering grows when a government adopts a new alphabet.

```
raw text
   │
   ├─ normalize_unicode()     NFC, strip zero-width, unify spaces
   │
   ├─ cyrillic_to_latin()     Cyrillic → canonical  (no-op if no Cyrillic)
   │
   ├─ fold_latin_variants()   ALL Latin spellings → canonical   ← always runs
   │
   └─ render(scheme)          canonical → target orthography
```

### Input folding — accept everything

`fold_latin_variants` recognizes every known written representation of each
sound and collapses it onto one internal token. For /oʻ/ alone that includes
`oʻ o' o’ o‘ o` o´ o′ oʼ ó ö ō ô ò õ ŏ ǒ`. This runs on *every* input,
regardless of which scheme it claims to be in, because a single document —
often a single sentence — mixes several.

### Output rendering — emit one

`render` goes the other way, from the canonical form to exactly one
orthography. Adding a fifth scheme means adding an enum member and a table to
`RENDER_TABLES`; no code changes.

## Internal canonical form

**The 1995 orthography with canonical Unicode modifier letters.**

| | codepoint |
|---|---|
| `oʻ`, `gʻ` tail | U+02BB MODIFIER LETTER TURNED COMMA |
| tutuq belgisi | U+02BC MODIFIER LETTER APOSTROPHE |
| `sh`, `ch`, `ng` | plain ASCII digraphs |

Why 1995: it is what the existing data uses, it is unambiguous (unlike ASCII
`'`, which is used for both the `oʻ` tail *and* the glottal stop), and it is
stable — the two modifier letters have well-defined Unicode identities, so
normalized text compares equal byte-for-byte.

## Convention decisions

Every judgement call is listed here, and each is a one-line change in
`mappings.py` if your corpus disagrees.

### `ц` (ts)
* **Word-initial → `s`**: `цирк` → `sirk`. This matches the official rules and
  Uzbek phonotactics (no initial /ts/ cluster).
* **Elsewhere → `ts`**: `конституция` → `konstitutsiya`.
* **Rendering**: only `LATIN_2019` writes it `c` (`konstituciya`).
* **Folding a bare `c`**: `c` is not a letter of the 1995 alphabet, so a
  standalone `c` (not part of `ch`) is folded to `ts` by default — this is what
  makes 2019-spelled input round-trip. The cost is foreign words:
  `Coca-Cola` → `Tsotsa-Tsola`. Pass `fold_bare_c=False` when the input is known
  to contain untransliterated foreign names. (For a TTS pipeline the default is
  usually right: `c` reaching the phonemizer unmapped is worse than an
  over-eager `ts`.)

### `е` / `ye`
* **`ye`** word-initially, after a vowel, or after `ъ`/`ь`:
  `Ер` → `Yer`, `Европа` → `Yevropa`, `оева` → `oyeva`, `объект` → `obʼyekt`.
* **`e`** after a consonant: `мен` → `men`.
* **`э` → `e`** always — it is never iotated, which is exactly what
  distinguishes it from `е`.
* `ё ю я` are always iotated: `yo yu ya`.

### Soft sign `ь` and hard sign `ъ`
* **`ь` → deleted.** It marks palatalization, which Uzbek Latin does not write:
  `медаль` → `medal`, `Ольга` → `Olga`. Its one visible effect is triggering the
  iotated `ye` in `ье`.
* **`ъ` → `ʼ` (U+02BC) between letters** — it is the tutuq belgisi, a real
  glottal stop / vowel-length marker that TTS must see: `маъно` → `maʼno`,
  `санъат` → `sanʼat`.
* **`ъ` → deleted at a word edge**, where it carries no sound.
* All apostrophe-like characters that are *not* the tail of `oʻ`/`gʻ` are
  unified on U+02BC.

### 2026 letter choices
* `ó` for /oʻ/ (carried over from 2019, not 1993's `ö` — this is also what keeps
  `LATIN_1993` and `LATIN_2026` distinguishable in this module).
* `ğ ş ç` for /gʻ ʃ tʃ/ (carried over from 1993).
* `ng` unchanged — no reform has touched it.
* `ts` unchanged — the 2026 reform does **not** adopt 2019's `c`.

### Other
* **`х` → `x`, `ҳ` → `h`** — kept distinct; the merger would lose a phonemic
  contrast the TTS voice may render differently.
* **`ж` → `j`** — Uzbek `ж` is /dʒ/, not Russian /ʒ/.
* **`ы` → `i`**, **`щ` → `shch`** — Russian loanwords only.
* **Casing** is preserved through multi-character mappings. A single capital is
  ambiguous between title case and all caps, so the neighbours decide: the
  letter to the right wins (`Şahar` → `Shahar`, `ŞAHAR` → `SHAHAR`), and when
  there is none, the letter to the left does (`ЁҒОЧ` → `YOGʻOCH`, but
  `Ш.` → `Sh.`).
* **Digits, punctuation, whitespace and foreign words pass through** untouched.
* **`sh`/`ch` are always read as digraphs.** `s`+`h` across a morpheme boundary
  would be misread, but in practice such words are spelled with an explicit
  tutuq belgisi (`Isʼhoq`), which the digraph rule does not touch.

## Known limitations

* `o'` is genuinely ambiguous between the `oʻ` letter and `o` + glottal stop.
  It is always folded to `oʻ`, which is right in the overwhelming majority of
  words.
* A morpheme-boundary `ts` (`Toshkent` + `siz`) becomes `c` under
  `LATIN_2019` rendering. This affects 2019 output only; the default 1995
  output is unaffected.

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

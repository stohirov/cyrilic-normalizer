"""Tests for the Uzbek text normalizer."""

from __future__ import annotations

import pytest

from uztext import (
    LatinScheme,
    cyrillic_to_latin,
    fold_latin_variants,
    normalize,
    normalize_unicode,
    render,
)
from uztext.mappings import CANON_G, CANON_O, MODIFIER_APOSTROPHE, TURNED_COMMA

ALL_SCHEMES = list(LatinScheme)

#: A sentence exercising the o and g letters, sh, ch, ng, ts and the tutuq
#: belgisi.
CANONICAL_SAMPLE = (
    "Oʻzbekiston Respublikasi gʻalabasi: shahar chegarasida "
    "koʻngil maʼnosi va konstitutsiya."
)


# --------------------------------------------------------------------------
# Round-trip stability
# --------------------------------------------------------------------------


@pytest.mark.parametrize("scheme", ALL_SCHEMES, ids=lambda s: s.name)
def test_render_fold_is_idempotent(scheme: LatinScheme) -> None:
    """render(fold(x)) is a fixed point: applying it twice changes nothing."""
    once = render(fold_latin_variants(CANONICAL_SAMPLE), scheme)
    twice = render(fold_latin_variants(once), scheme)
    assert once == twice


@pytest.mark.parametrize("scheme", ALL_SCHEMES, ids=lambda s: s.name)
def test_round_trip_through_canonical(scheme: LatinScheme) -> None:
    """Rendering to a scheme and folding back recovers the canonical form."""
    rendered = render(CANONICAL_SAMPLE, scheme)
    assert fold_latin_variants(rendered) == CANONICAL_SAMPLE


@pytest.mark.parametrize("scheme", ALL_SCHEMES, ids=lambda s: s.name)
def test_normalize_is_idempotent(scheme: LatinScheme) -> None:
    """The full pipeline is stable when fed its own output."""
    once = normalize("Ўзбекистон Республикаси ғалабаси", scheme)
    assert normalize(once, scheme) == once


# --------------------------------------------------------------------------
# Cross-scheme folding: accept everything, emit one
# --------------------------------------------------------------------------

O_VARIANTS = [
    "oʻzbek",  # 1995 canonical, o + U+02BB
    "o'zbek",  # ASCII apostrophe
    "o’zbek",  # right single quotation mark
    "o‘zbek",  # left single quotation mark
    "o`zbek",  # backtick
    "oʼzbek",  # modifier letter apostrophe, U+02BC
    "ózbek",  # 2019, o-acute
    "özbek",  # 1993 and 2026, o-umlaut
    "ōzbek",  # 2021 draft, o-macron
]

G_VARIANTS = [
    "gʻalaba",  # 1995 canonical, g + U+02BB
    "g'alaba",  # ASCII apostrophe
    "g’alaba",  # right single quotation mark
    "ǵalaba",  # 2019, g-acute
    "ğalaba",  # 1993 and 2026, g-breve
    "ḡalaba",  # 2021 draft, g-macron
]

SH_VARIANTS = ["shahar", "şahar", "șahar", "šahar"]
CH_VARIANTS = ["chiroq", "çiroq", "čiroq", "ćiroq"]


@pytest.mark.parametrize(
    "variants, expected",
    [
        (O_VARIANTS, "oʻzbek"),
        (G_VARIANTS, "gʻalaba"),
        (SH_VARIANTS, "shahar"),
        (CH_VARIANTS, "chiroq"),
    ],
    ids=["o", "g", "sh", "ch"],
)
def test_all_variants_fold_to_one_canonical_token(
    variants: list[str], expected: str
) -> None:
    assert {fold_latin_variants(v) for v in variants} == {expected}


@pytest.mark.parametrize("scheme", ALL_SCHEMES, ids=lambda s: s.name)
@pytest.mark.parametrize("variants", [O_VARIANTS, G_VARIANTS, SH_VARIANTS, CH_VARIANTS])
def test_variants_render_identically(variants: list[str], scheme: LatinScheme) -> None:
    """However it was spelled on input, one input scheme -> one output string."""
    outputs = {normalize(v, scheme) for v in variants}
    assert len(outputs) == 1, outputs


def test_mixed_orthography_in_one_string() -> None:
    """A single sentence written in three orthographies at once."""
    mixed = "Ózbekiston va o'zbek va özbek va oʻzbek"
    assert normalize(mixed) == "Oʻzbekiston va oʻzbek va oʻzbek va oʻzbek"
    assert normalize(mixed, LatinScheme.LATIN_2026) == (
        "Özbekiston va özbek va özbek va özbek"
    )


# --------------------------------------------------------------------------
# Rendering per scheme
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scheme, expected",
    [
        (LatinScheme.LATIN_1993, "Özbekiston"),
        (LatinScheme.LATIN_1995, "Oʻzbekiston"),
        (LatinScheme.LATIN_2019, "Ózbekiston"),
        (LatinScheme.LATIN_2026, "Özbekiston"),
    ],
    ids=lambda v: getattr(v, "name", v),
)
def test_cyrillic_uzbekistan_per_scheme(scheme: LatinScheme, expected: str) -> None:
    assert normalize("Ўзбекистон", scheme) == expected


@pytest.mark.parametrize(
    "scheme, expected",
    [
        (LatinScheme.LATIN_1993, "ğalaba"),
        (LatinScheme.LATIN_1995, "gʻalaba"),
        (LatinScheme.LATIN_2019, "ǵalaba"),
        (LatinScheme.LATIN_2026, "ğalaba"),
    ],
    ids=lambda v: getattr(v, "name", v),
)
def test_g_letter_per_scheme(scheme: LatinScheme, expected: str) -> None:
    assert normalize("ғалаба", scheme) == expected


@pytest.mark.parametrize(
    "scheme, expected",
    [
        (LatinScheme.LATIN_1993, "şaharça"),
        (LatinScheme.LATIN_1995, "shaharcha"),
        (LatinScheme.LATIN_2019, "shaharcha"),
        (LatinScheme.LATIN_2026, "şaharça"),
    ],
    ids=lambda v: getattr(v, "name", v),
)
def test_digraphs_per_scheme(scheme: LatinScheme, expected: str) -> None:
    assert normalize("шаҳарча", scheme) == expected


def test_render_1995_is_identity_on_canonical() -> None:
    assert render(CANONICAL_SAMPLE, LatinScheme.LATIN_1995) == CANONICAL_SAMPLE


def test_render_rejects_non_scheme() -> None:
    with pytest.raises(TypeError):
        render("oʻzbek", "LATIN_1995")  # type: ignore[arg-type]


def test_render_defaults_to_1995() -> None:
    assert render(CANONICAL_SAMPLE) == CANONICAL_SAMPLE


# --------------------------------------------------------------------------
# Cyrillic transliteration
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cyrillic, expected",
    [
        ("Ўзбекистон", "Oʻzbekiston"),
        ("Тошкент", "Toshkent"),
        ("Самарқанд", "Samarqand"),
        ("Чирчиқ", "Chirchiq"),
        ("Хива", "Xiva"),  # CYRILLIC HA -> x
        ("Ҳудуд", "Hudud"),  # CYRILLIC HA WITH DESCENDER -> h
        ("жуда", "juda"),  # CYRILLIC ZHE -> j
        ("ёшлар", "yoshlar"),  # CYRILLIC IO -> yo
        ("юксак", "yuksak"),  # CYRILLIC YU -> yu
        ("ярим", "yarim"),  # CYRILLIC YA -> ya
        ("ғоя", "gʻoya"),
        ("Гўзал", "Goʻzal"),
    ],
)
def test_cyrillic_to_latin_basics(cyrillic: str, expected: str) -> None:
    assert cyrillic_to_latin(cyrillic) == expected


@pytest.mark.parametrize(
    "cyrillic, expected",
    [
        ("Ер", "Yer"),  # word-initial IE -> ye
        ("Европа", "Yevropa"),  # word-initial IE -> ye
        ("мен", "men"),  # after consonant -> e
        ("келди", "keldi"),  # after consonant -> e
        ("оева", "oyeva"),  # after vowel -> ye
        ("объект", "obʼyekt"),  # after hard sign -> ye; hard sign -> tutuq belgisi
        ("Эркин", "Erkin"),  # CYRILLIC E is never iotated
    ],
)
def test_cyrillic_e_and_ye(cyrillic: str, expected: str) -> None:
    assert cyrillic_to_latin(cyrillic) == expected


@pytest.mark.parametrize(
    "cyrillic, expected",
    [
        ("цирк", "sirk"),  # word-initial TSE -> s
        ("Цюрих", "Syurix"),  # word-initial TSE -> s, casing preserved
        ("конституция", "konstitutsiya"),  # medial TSE -> ts
        ("революция", "revolyutsiya"),
    ],
)
def test_cyrillic_ts(cyrillic: str, expected: str) -> None:
    assert cyrillic_to_latin(cyrillic) == expected


@pytest.mark.parametrize(
    "cyrillic, expected",
    [
        ("маъно", "maʼno"),  # medial hard sign -> tutuq belgisi
        ("таъриф", "taʼrif"),
        ("санъат", "sanʼat"),
        ("медаль", "medal"),  # soft sign dropped
        ("Ольга", "Olga"),  # soft sign dropped
        ("асосъ", "asos"),  # word-final hard sign dropped
    ],
)
def test_cyrillic_soft_and_hard_signs(cyrillic: str, expected: str) -> None:
    assert cyrillic_to_latin(cyrillic) == expected


def test_shcha() -> None:
    assert cyrillic_to_latin("Щукин") == "Shchukin"
    assert cyrillic_to_latin("ЩУКИН") == "SHCHUKIN"


@pytest.mark.parametrize(
    "scheme, expected",
    [
        (LatinScheme.LATIN_1995, "konstitutsiya"),
        (LatinScheme.LATIN_2019, "konstituciya"),  # 2019 spells /ts/ as c
        (LatinScheme.LATIN_2026, "konstitutsiya"),
        (LatinScheme.LATIN_1993, "konstitutsiya"),
    ],
    ids=lambda v: getattr(v, "name", v),
)
def test_ts_rendering_per_scheme(scheme: LatinScheme, expected: str) -> None:
    assert normalize("конституция", scheme) == expected


def test_bare_c_folds_to_ts_by_default() -> None:
    """2019-spelled input is recovered without needing to know its scheme."""
    assert fold_latin_variants("konstituciya") == "konstitutsiya"
    assert normalize("konstituciya") == "konstitutsiya"


def test_bare_c_folding_can_be_disabled_for_foreign_words() -> None:
    assert fold_latin_variants("Coca-Cola", fold_bare_c=False) == "Coca-Cola"
    assert normalize("Coca-Cola", fold_bare_c=False) == "Coca-Cola"


def test_ch_is_never_split_by_bare_c_folding() -> None:
    assert fold_latin_variants("chiroq") == "chiroq"
    assert fold_latin_variants("CHIROQ") == "CHIROQ"


# --------------------------------------------------------------------------
# Casing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("shahar", "shahar"),  # all lower
        ("Shahar", "Shahar"),  # title
        ("SHAHAR", "SHAHAR"),  # all caps
        ("şahar", "shahar"),
        ("Şahar", "Shahar"),
        ("ŞAHAR", "SHAHAR"),
    ],
)
def test_casing_sh(text: str, expected: str) -> None:
    assert fold_latin_variants(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("shahar", "şahar"),
        ("Shahar", "Şahar"),
        ("SHAHAR", "ŞAHAR"),
    ],
)
def test_casing_sh_rendering_2026(text: str, expected: str) -> None:
    assert normalize(text, LatinScheme.LATIN_2026) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("o'zbek", "oʻzbek"),
        ("O'zbek", "Oʻzbek"),
        ("O'ZBEK", "OʻZBEK"),
        ("Ózbek", "Oʻzbek"),
        ("ÓZBEK", "OʻZBEK"),
    ],
)
def test_casing_o(text: str, expected: str) -> None:
    assert fold_latin_variants(text) == expected


@pytest.mark.parametrize(
    "cyrillic, expected",
    [
        ("ЁҒОЧ", "YOGʻOCH"),  # trailing capital inside an all-caps word
        ("ЧИРЧИҚ", "CHIRCHIQ"),
        ("ЩУКИН", "SHCHUKIN"),
        ("ГЎЗАЛ", "GOʻZAL"),
    ],
)
def test_casing_trailing_capital_in_all_caps_word(cyrillic: str, expected: str) -> None:
    """A capital with no letter to its right takes its case from the left."""
    assert cyrillic_to_latin(cyrillic) == expected


def test_casing_single_letter_word() -> None:
    """A lone capital with no following letter is title-cased, not shouted."""
    assert fold_latin_variants("Ó") == "Oʻ"
    assert normalize("Ш.", LatinScheme.LATIN_1995) == "Sh."


def test_casing_sentence_and_title() -> None:
    assert normalize("Ўзбекистон Республикаси Олий Мажлиси") == (
        "Oʻzbekiston Respublikasi Oliy Majlisi"
    )
    assert normalize("ЎЗБЕКИСТОН РЕСПУБЛИКАСИ") == "OʻZBEKISTON RESPUBLIKASI"


# --------------------------------------------------------------------------
# Unicode normalization, mixed script, pass-through
# --------------------------------------------------------------------------


def test_normalize_unicode_composes_and_cleans() -> None:
    assert normalize_unicode("ózbek") == "ózbek"  # NFC composition
    assert normalize_unicode("a ​b") == "a b"  # nbsp + zero width
    assert normalize_unicode("  koʻp   boʻsh  ") == "koʻp boʻsh"
    assert normalize_unicode("") == ""


def test_decomposed_input_folds() -> None:
    """o + combining acute (not NFC) still folds, via the pipeline's NFC step."""
    assert normalize("ózbek") == "oʻzbek"


def test_apostrophe_unification() -> None:
    """Every tutuq belgisi variant lands on U+02BC; o/g tails on U+02BB."""
    for raw in ["ma'no", "ma’no", "ma‘no", "maʼno", "ma`no"]:
        assert normalize(raw) == "ma" + MODIFIER_APOSTROPHE + "no"
    assert normalize("o'zbek") == "o" + TURNED_COMMA + "zbek"
    assert CANON_O.endswith(TURNED_COMMA) and CANON_G.endswith(TURNED_COMMA)


def test_mixed_script() -> None:
    assert normalize("Ўзбекистон Airways 2026-yilda") == (
        "Oʻzbekiston Airways 2026-yilda"
    )


def test_mixed_script_and_orthography_together() -> None:
    text = "Тошкент shahri, Sirdaryo viloyati, Qashqadaryo — ЎЗБЕКИСТОН"
    assert normalize(text) == (
        "Toshkent shahri, Sirdaryo viloyati, Qashqadaryo — OʻZBEKISTON"
    )
    assert normalize(text, LatinScheme.LATIN_2026) == (
        "Toşkent şahri, Sirdaryo viloyati, Qaşqadaryo — ÖZBEKISTON"
    )


@pytest.mark.parametrize(
    "text",
    [
        "2026",
        "12,5 %",
        "«qoʻshtirnoq»",
        "e-mail: test@example.com",
        "!?.,;:()[]{}",
        "",
    ],
)
def test_pass_through(text: str) -> None:
    """Digits and punctuation survive every stage unchanged."""
    assert normalize(text, fold_bare_c=False) == normalize_unicode(text)


def test_empty_and_whitespace_inputs() -> None:
    assert normalize("") == ""
    assert cyrillic_to_latin("") == ""
    assert fold_latin_variants("") == ""
    assert render("", LatinScheme.LATIN_2026) == ""


# --------------------------------------------------------------------------
# Purity
# --------------------------------------------------------------------------


def test_functions_do_not_mutate_input() -> None:
    original = "Ўзбекистон o'zbek şahar"
    copy = str(original)
    for func in (normalize_unicode, cyrillic_to_latin, fold_latin_variants, normalize):
        func(original)
    assert original == copy


def test_repeated_calls_are_deterministic() -> None:
    text = "Ғалаба ko'chasi, ŞAHAR"
    assert normalize(text) == normalize(text)

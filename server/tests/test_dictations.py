"""WP-5/WP-6: ganze Diktate aus Anhang B / C des Reports durch die Pipeline."""

from medvox.normalize import ToothRef, normalize


def test_d01_spoken():
    result = normalize(
        "Zahn drei sechs mesial okklusal distal Karies profunda, Infiltrationsanästhesie mit Artikain, "
        "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."
    )
    assert result.text == (
        "Zahn 36 mod Karies profunda, Infiltrationsanästhesie mit Artikain, "
        "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."
    )
    assert result.teeth == [ToothRef(36, "mod")]


def test_d06_spoken():
    result = normalize(
        "Eins vier distal okklusal Sekundärkaries unter alter Amalgamfüllung, Amalgam entfernt, Unterfüllung mit "
        "Glasionomerzement, Kompositfüllung MOD, dreiflächig, GOZ zwei eins null null als Zusatzleistung."
    )
    assert result.text == (
        "14 do Sekundärkaries unter alter Amalgamfüllung, Amalgam entfernt, Unterfüllung mit "
        "Glasionomerzement, Kompositfüllung mod, dreiflächig, GOZ 2100 als Zusatzleistung."
    )
    assert result.teeth == [ToothRef(14, "do")]


def test_d11_whisper_de_prompt():
    result = normalize(
        "36, 37 okklusal, Karies, Füllungen mit Komposit, jeweils einflächig, BEMA 13A zweimal, "
        "Zusatzleistung GOZ 2060."
    )
    assert result.text == (
        "36, 37 o, Karies, Füllungen mit Komposit, jeweils einflächig, BEMA 13a 2x, Zusatzleistung GOZ 2060."
    )
    assert result.teeth == [ToothRef(36, "o"), ToothRef(37, "o")]


def test_d11_whisper_en_no_prompt_after_correction():
    from medvox.lexicon import correct

    corrected, _ = correct("36-37 Occlusal Caries, Füllungen mit Composite, jeweils einflächig, BEMA 13a 2x, "
                           "Zusatzleistung Goetz 2060.")
    result = normalize(corrected)
    assert result.text == (
        "36-37 o Karies, Füllungen mit Komposit, jeweils einflächig, BEMA 13a 2x, Zusatzleistung GOZ 2060."
    )
    assert result.teeth == [ToothRef(36, "o"), ToothRef(37, "o")]


def test_d12_planned_extraction_keeps_both_references():
    result = normalize(
        "Vier acht Perikoronitis, Spülung mit Chlorhexidin, Einlage, Ibuprofen sechshundert verordnet, "
        "Wiedervorlage in zwei Tagen, danach Extraktion vier acht planen."
    )
    assert result.text == (
        "48 Perikoronitis, Spülung mit Chlorhexidin, Einlage, Ibuprofen 600 verordnet, "
        "Wiedervorlage in 2 Tagen, danach Extraktion 48 planen."
    )
    assert [t.fdi for t in result.teeth] == [48, 48]

from midori import anki, jmdict
from midori.parse import parse_bookmarks


def test_parse_quoted_tsv(tmp_path):
    p = tmp_path / "b.tsv"
    p.write_text('"隙"\t"すき"\t"gap, space"\n', encoding="utf-8")
    rows = parse_bookmarks(str(p))
    assert rows == [{"expression": "隙", "reading": "すき", "source_gloss": "gap, space"}]


def test_match_prefers_pair_over_expression():
    entry, status, _ = jmdict.match("隙", "すき", "gap, space",
                                    entries=jmdict.STUB_ENTRIES)
    assert entry["jmdict_seq"] == 9000007
    assert status == "exact"


def test_missing_and_ambiguous_statuses():
    entry, status, _ = jmdict.match("未知語", "みちご", "unknown",
                                    entries=jmdict.STUB_ENTRIES)
    assert entry is None and status == "missing"


def test_kana_expression_matches_reading_form():
    entries = [{
        "jmdict_seq": 1400550, "written_forms": ["燥ぐ"], "readings": ["はしゃぐ"],
        "priority": [], "pos": ["Godan verb"], "entry_type": "vocab",
        "senses": [{
            "glosses": ["to make merry"],
            "labels": {"pos": [], "misc": [], "field": [], "dial": []},
            "restrictions": {"stagk": [], "stagr": []},
            "xrefs": [], "antonyms": [],
        }],
        "variants": {},
    }]
    entry, status, _ = jmdict.match("はしゃぐ", "はしゃぐ", "to make merry",
                                    entries=entries)
    assert status == "exact" and entry["jmdict_seq"] == 1400550


def test_live_jmdict_seq():
    import pytest
    entries = jmdict.live_entries("理不尽")
    if not entries:
        pytest.skip("live JMdict unavailable")
    assert entries[0]["jmdict_seq"] == 1550120


def test_guid_stable_from_seq():
    a = anki.stable_guid(9000004, "理不尽", "りふじん")
    b = anki.stable_guid(9000004, "理不尽", "りふじん")
    c = anki.stable_guid(None, "理不尽", "りふじん")
    assert a == b and a != c


def test_furigana_per_char_and_kana():
    assert anki.furigana_for("理不尽", "りふじん") == "理[り]不[ふ]尽[じん]"
    assert anki.furigana_for("だらけ", "だらけ") == "だらけ"
    assert anki.furigana_for("収集", "しゅうしゅう") == "収集[しゅうしゅう]"


def test_merge_reuses_unchanged_rows_verbatim():
    from midori.cli import build_all, fingerprint
    bm_old = {"expression": "収集", "reading": "しゅうしゅう", "source_gloss": "collect"}
    prior_rec = {"expression": "収集", "reading": "しゅうしゅう",
                 "source_gloss": "collect", "guid": "stable123",
                 "generated": {"usage": "hand-edited"}}
    assert fingerprint(bm_old) == fingerprint(prior_rec)
    bm_new = {"expression": "隙", "reading": "すき", "source_gloss": "gap"}
    records, reused = build_all([bm_old, bm_new], {fingerprint(prior_rec): prior_rec},
                                entries=jmdict.STUB_ENTRIES)
    assert reused == 1
    assert records[0] == prior_rec
    assert records[1]["match_status"] == "exact"


def test_run_stats_counts_and_diff():
    from midori.cli import fingerprint, run_stats
    kept = {"expression": "隙", "reading": "すき", "source_gloss": "gap",
            "match_status": "exact", "candidates": [1]}
    new = {"expression": "残酷", "reading": "ざんこく", "source_gloss": "cruel",
           "match_status": "missing", "candidates": []}
    prior = {fingerprint(kept): kept,
             fingerprint({"expression": "削除", "reading": "さくじょ",
                          "source_gloss": "gone"}):
             {"expression": "削除", "reading": "さくじょ"}}
    stats = run_stats([kept, new], prior, "in.tsv", "out", "deck")
    assert (stats["total"], stats["exact"], stats["missing"]) == (2, 1, 1)
    assert (stats["reused"], stats["new"]) == (1, 1)
    assert stats["dropped"] == ["削除"]
    assert stats["review"] == [{"expression": "残酷", "reading": "ざんこく",
                                "status": "missing", "candidates": []}]
    assert stats["deck"] == "deck"


def test_default_outdir_sits_next_to_input():
    from midori.cli import default_outdir
    assert default_outdir("/tmp/words.tsv") == "/tmp/words_anki"


def test_furigana_html_ruby_per_kanji():
    assert anki.furigana_html("理不尽", "りふじん") == (
        "<ruby>理<rt>り</rt></ruby>"
        "<ruby>不<rt>ふ</rt></ruby>"
        "<ruby>尽<rt>じん</rt></ruby>"
    )
    assert anki.furigana_html("だらけ", "だらけ") == "だらけ"


def test_midori_url_encodes():
    from urllib.parse import quote
    assert anki.midori_url("理不尽") == "midori://search?text=" + quote("理不尽", safe="")
    assert anki.midori_url("a&b") == "midori://search?text=a%26b"

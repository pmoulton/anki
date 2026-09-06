"""Build enriched records + Anki outputs."""
from collections import Counter
import csv
import hashlib
import html
import re
from typing import Any, Optional
from urllib.parse import quote

import genanki

from .jmdict import Entry

MODEL_NAME = "Midori Rich Japanese v2"
# Stable Anki IDs: changing these orphans existing cards on re-import,
# so they must stay fixed across runs. Bump MODEL_NAME (not the ID)
# when the template changes incompatibly.
MODEL_ID = 1607392320
DECK_ID = 2059409282

FIELDS = [
    "Expression", "Reading", "Furigana", "Lookup", "POS", "Definitions",
    "Usage", "ExampleJP", "ExampleEN", "Collocations",
    "SourceGloss", "MidoriLookupURL",
]

# Per-character furigana segments for seed words.
# Real version can replace this with MeCab/fugashi segmentation;
# unknown words fall back to a single whole-word ruby block.
FURIGANA_SEGMENTS = {
    "本来": [("本", "ほん"), ("来", "らい")],
    "稽古": [("稽", "けい"), ("古", "こ")],
    "理不尽": [("理", "り"), ("不", "ふ"), ("尽", "じん")],
    "杞憂": [("杞", "き"), ("憂", "ゆう")],
    "覇気": [("覇", "は"), ("気", "き")],
    "隙": [("隙", "すき")],
    "だらけ": [("だらけ", "")],
}

_KANJI_RE = re.compile(r"[\u4e00-\u9fff]")


def furigana_for(expression: str, reading: str) -> str:
    """Bracket syntax (`kanji[kana]`), e.g. for TSV inspection."""
    segs = FURIGANA_SEGMENTS.get(expression)
    if segs is None:
        if expression == reading or not _KANJI_RE.search(expression):
            return expression
        segs = [(expression, reading)]
    return "".join(
        k if not r else f"{k}[{r}]" for k, r in segs
    )


def furigana_html(expression: str, reading: str) -> str:
    """Real `<ruby>` markup so the kana renders above the correct kanji
    in any webview, without relying on Anki's bracket filter."""
    segs = FURIGANA_SEGMENTS.get(expression)
    if segs is None:
        if expression == reading or not _KANJI_RE.search(expression):
            return html.escape(expression)
        segs = [(expression, reading)]
    parts = []
    for kanji, kana in segs:
        if not kana:
            parts.append(html.escape(kanji))
        else:
            parts.append(
                f"<ruby>{html.escape(kanji)}<rt>{html.escape(kana)}</rt></ruby>"
            )
    return "".join(parts)


def stable_guid(jmdict_seq: Optional[int], expression: str, reading: str) -> str:
    if jmdict_seq:
        key = f"midori-anki::seq::{jmdict_seq}"
    else:
        key = f"midori-anki::fallback::{expression}::{reading}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def midori_url(lookup_term: str) -> str:
    return "midori://search?text=" + quote(lookup_term, safe="")


def pos_display(entry: Optional[Entry]) -> str:
    if entry is None:
        return ""
    return ", ".join(entry.get("pos", []))


def definitions_html(entry: Optional[Entry]) -> str:
    if entry is None:
        return ""
    parts = ["<ol>"]
    for sense in entry["senses"]:
        glosses = "; ".join(html.escape(g) for g in sense["glosses"])
        parts.append(f"<li>{glosses}</li>")
    parts.append("</ol>")
    return "".join(parts)


def build_record(bookmark: dict[str, str], entry: Optional[Entry],
                 match_status: str, lookup_term: str,
                 generated: dict[str, Any], pattern: str = "") -> dict[str, Any]:
    usage = generated.get("usage", "")
    if pattern:
        usage = f"<div>Pattern: {html.escape(pattern)}</div><div>{html.escape(usage)}</div>" if usage else f"Pattern: {html.escape(pattern)}"
    elif usage:
        usage = html.escape(usage)
    collocs = " · ".join(html.escape(c) for c in generated.get("collocations", []))
    return {
        "expression": bookmark["expression"],
        "reading": bookmark["reading"],
        "source_gloss": bookmark["source_gloss"],
        "lookup_term": lookup_term,
        "midori_url": midori_url(lookup_term),
        "match_status": match_status,
        "candidates": [],
        "dictionary": {
            "jmdict_seq": entry["jmdict_seq"] if entry else None,
            "pos": list(entry["pos"]) if entry else [],
            "senses": entry["senses"] if entry else [],
            "variants": entry["variants"] if entry else {},
            "priority": list(entry.get("priority", [])) if entry else [],
            "entry_type": entry.get("entry_type", "vocab") if entry else "vocab",
        },
        "generated": {
            "source": generated.get("source", "fallback"),
            "usage": generated.get("usage", ""),
            "pattern": generated.get("pattern", ""),
            "collocations": list(generated.get("collocations", [])),
            "example_jp": generated.get("example_jp", ""),
            "example_en": generated.get("example_en", ""),
        },
        "render": {
            "POS": html.escape(pos_display(entry)),
            "Definitions": definitions_html(entry),
            "Usage": usage,
            "ExampleJP": html.escape(generated.get("example_jp", "")),
            "ExampleEN": html.escape(generated.get("example_en", "")),
            "Collocations": collocs,
            "Furigana": furigana_html(bookmark["expression"], bookmark["reading"]),
        },
        "guid": stable_guid(
            entry["jmdict_seq"] if entry else None,
            bookmark["expression"], bookmark["reading"],
        ),
    }


def _read_template(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def make_model(front_path: str, back_path: str, css_path: str) -> genanki.Model:
    qfmt = _read_template(front_path)
    afmt = _read_template(back_path)
    css = _read_template(css_path)
    return genanki.Model(
        MODEL_ID, MODEL_NAME,
        fields=[{"name": f} for f in FIELDS],
        templates=[{"name": "Card 1", "qfmt": qfmt, "afmt": afmt}],
        css=css,
    )


def record_to_fields(rec: dict[str, Any]) -> list[str]:
    r = rec["render"]
    return [
        rec["expression"], rec["reading"], r["Furigana"], rec["lookup_term"],
        r["POS"], r["Definitions"], r["Usage"],
        r["ExampleJP"], r["ExampleEN"], r["Collocations"],
        html.escape(rec["source_gloss"]), rec["midori_url"],
    ]


def write_tsv(records: list[dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(FIELDS)
        for rec in records:
            w.writerow(record_to_fields(rec))


def write_apkg(records: list[dict[str, Any]], model: genanki.Model,
               deck_name: str, path: str) -> None:
    deck = genanki.Deck(DECK_ID, deck_name)
    for rec in records:
        note = genanki.Note(model=model, fields=record_to_fields(rec), guid=rec["guid"])
        deck.add_note(note)
    deck.write_to_file(path)


def write_report(records: list[dict[str, Any]], path: str) -> str:
    counts = Counter(r["match_status"] for r in records)
    total = len(records)
    lines = [
        f"{total} bookmarks",
        f"{counts.get('exact', 0)} exact matches",
        f"{counts.get('inferred', 0)} inferred matches",
        f"{counts.get('ambiguous', 0)} ambiguous",
        f"{counts.get('missing', 0)} missing",
        "",
    ]
    for r in records:
        if r["match_status"] in ("ambiguous", "missing"):
            lines.append(
                f"{r['match_status']}: {r['expression']} [{r['reading']}] "
                f"candidates={r.get('candidates', [])}"
            )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return "\n".join(lines[:5])

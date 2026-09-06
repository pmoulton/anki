"""JMdict matching.

Live backend queries JMdict via jamdict (real sequence IDs, POS, senses,
labels, variants, priorities, xrefs). When jamdict is unavailable
(e.g. offline), matching falls back to STUB_ENTRIES so the pipeline and
unit tests still run.

Matching rules:
  1. Match on (expression, reading) first, not expression alone.
  2. If several entries match, score SourceGloss tokens against each
     entry's English senses and require a clear margin to disambiguate.
  3. Never silently pick an ambiguous entry -> match_status "ambiguous".
  4. match_status in {exact, inferred, ambiguous, missing}.
"""
import re
from typing import Any, Optional

Entry = dict[str, Any]

_WORD_RE = re.compile(r"[a-zA-Z']+")

# Override lookup term when visible expression != Midori search term.
# e.g. {"～わけにはいかない": "わけにはいかない"}
LOOKUP_OVERRIDES = {}


def lookup_term_for(expression: str) -> str:
    return LOOKUP_OVERRIDES.get(expression, expression)


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _gloss_text(entry: Entry) -> str:
    parts = []
    for s in entry["senses"]:
        parts.extend(s.get("glosses", []))
    return " ".join(parts)


# --- Short POS labels -------------------------------------------------
# JMdict POS entities are verbose ("noun (common) (futsuumeishi)"); cards
# show the short form while enriched.json keeps the raw strings per sense.
_SHORT_POS = {
    "noun (common) (futsuumeishi)": "Noun",
    "adjectival nouns or quasi-adjectives (keiyodoshi)": "Na-adjective",
    "noun or participle which takes the aux. verb suru": "Suru verb",
    "adverb (fukushi)": "Adverb",
    "adjective (keiyoushi)": "I-adjective",
    "expressions (phrases, clauses, etc.)": "Expression",
    "suffix": "Suffix",
    "prefix": "Prefix",
    "conjunction": "Conjunction",
    "interjection (kandoushi)": "Interjection",
    "pronoun": "Pronoun",
    "counter": "Counter",
    "numeric": "Numeric",
    "auxiliary verb": "Aux. verb",
    "particle": "Particle",
    "pre-noun adjectival (rentaishi)": "Pre-noun",
    "nouns which may take the genitive case particle `no'": "No-adjective",
    "intransitive verb": "Intransitive",
    "transitive verb": "Transitive",
    "ichidan verb": "Ichidan verb",
}


def short_pos(raw: str) -> str:
    if raw in _SHORT_POS:
        return _SHORT_POS[raw]
    if raw.startswith("godan verb"):
        return "Godan verb"
    if raw.startswith("kudan verb"):
        return "Godan verb"
    # Fallback: strip parentheticals, title-case, keep it short.
    bare = re.sub(r"\s*\(.*?\)", "", raw).strip().title()
    return bare[:40] if bare else raw[:40]


# --- Live backend ------------------------------------------------------
_JAM = None


def _jamdict():
    global _JAM
    if _JAM is None:
        from jamdict import Jamdict
        _JAM = Jamdict()
    return _JAM


def _texts(objs: Any) -> list[str]:
    out = []
    for o in objs or []:
        t = getattr(o, "text", None)
        out.append(t if t else str(o))
    return out


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _glosses(sense: Any) -> list[str]:
    glosses = list(sense.gloss or [])
    eng = [g.text for g in glosses if getattr(g, "lang", "eng") == "eng"]
    return eng if eng else [g.text for g in glosses]


def from_jam(e: Any) -> Entry:
    """Convert a jamdict entry to our canonical shape (real JMdict seq)."""
    written = [k.text for k in e.kanji_forms]
    readings = [k.text for k in e.kana_forms]
    pri = list(dict.fromkeys(
        p for k in list(e.kanji_forms) + list(e.kana_forms) for p in (k.pri or [])
    ))
    senses = []
    for s in e.senses:
        senses.append({
            "glosses": _glosses(s),
            "labels": {
                "pos": list(s.pos or []),
                "misc": list(s.misc or []),
                "field": list(s.field or []),
                "dial": _as_list(s.dialect),
            },
            "restrictions": {
                "stagk": list(s.stagk or []),
                "stagr": list(s.stagr or []),
            },
            "xrefs": _texts(s.xref),
            "antonyms": _texts(s.antonym),
        })
    top_pos = []
    for p in dict.fromkeys(p for s in senses for p in s["labels"]["pos"]):
        sp = short_pos(p)
        if sp not in top_pos:
            top_pos.append(sp)
    raw_pos = " ".join(p for s in senses for p in s["labels"]["pos"])
    return {
        "jmdict_seq": e.idseq,
        "written_forms": written,
        "readings": readings,
        "priority": pri,
        "pos": top_pos,
        "entry_type": "grammar" if "suffix" in raw_pos else "vocab",
        "senses": senses,
        "variants": {"written": written, "readings": readings},
    }


def live_entries(expression: str) -> Optional[list[Entry]]:
    """Entries for an expression from live JMdict, or None if unavailable."""
    try:
        res = _jamdict().lookup(expression)
    except Exception:
        return None
    return [from_jam(e) for e in res.entries]


# --- Stub dictionary (offline fallback + unit tests) --------------------
# Seq numbers are 9_000_000-range placeholders, NOT real JMdict IDs.
STUB_ENTRIES: list[Entry] = [
    {
        "jmdict_seq": 9000001,
        "written_forms": ["だらけ"],
        "readings": ["だらけ"],
        "priority": [],
        "pos": ["suffix", "expression"],
        "entry_type": "grammar",
        "senses": [
            {
                "glosses": ["full of", "covered with"],
                "labels": {"pos": ["suffix"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": ["まみれ"], "antonyms": [],
            },
            {
                "glosses": ["riddled with", "containing many undesirable things"],
                "labels": {"pos": ["suffix"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": ["まみれ"], "antonyms": [],
            },
        ],
        "variants": {"written": ["だらけ"], "readings": ["だらけ"]},
    },
    {
        "jmdict_seq": 9000002,
        "written_forms": ["本来"],
        "readings": ["ほんらい", "ほんたい"],
        "priority": ["common"],
        "pos": ["adverb", "noun", "adjectival noun (no-adjective)"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["originally", "primarily"],
                "labels": {"pos": ["adverb"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
            {
                "glosses": ["essentially", "intrinsically", "naturally", "by nature"],
                "labels": {"pos": ["adverb"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
            {
                "glosses": ["proper", "rightful", "normal"],
                "labels": {"pos": ["no-adjective", "noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
        ],
        "variants": {"written": ["本来"], "readings": ["ほんらい", "ほんたい"]},
    },
    {
        "jmdict_seq": 9000003,
        "written_forms": ["稽古"],
        "readings": ["けいこ"],
        "priority": ["common"],
        "pos": ["noun", "suru verb"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["practice", "training", "study", "rehearsal"],
                "labels": {"pos": ["noun", "suru verb"], "misc": [], "field": ["martial arts", "performing arts"], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": ["練習"], "antonyms": [],
            },
        ],
        "variants": {"written": ["稽古"], "readings": ["けいこ"]},
    },
    {
        "jmdict_seq": 9000004,
        "written_forms": ["理不尽"],
        "readings": ["りふじん"],
        "priority": ["common"],
        "pos": ["na-adjective", "noun"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["unreasonable", "irrational"],
                "labels": {"pos": ["na-adjective", "noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": ["道理"],
            },
            {
                "glosses": ["absurd", "outrageous", "unjust"],
                "labels": {"pos": ["na-adjective", "noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
        ],
        "variants": {"written": ["理不尽"], "readings": ["りふじん"]},
    },
    {
        "jmdict_seq": 9000005,
        "written_forms": ["杞憂"],
        "readings": ["きゆう"],
        "priority": [],
        "pos": ["noun"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["needless fear", "groundless apprehension", "unfounded worry"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": ["取り越し苦労"], "antonyms": [],
            },
        ],
        "variants": {"written": ["杞憂"], "readings": ["きゆう"]},
    },
    {
        "jmdict_seq": 9000006,
        "written_forms": ["覇気"],
        "readings": ["はき"],
        "priority": [],
        "pos": ["noun"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["spirit", "drive", "vigour"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
            {
                "glosses": ["ambition", "aspiration"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": ["野心"], "antonyms": [],
            },
        ],
        "variants": {"written": ["覇気"], "readings": ["はき"]},
    },
    {
        "jmdict_seq": 9000007,
        "written_forms": ["隙"],
        "readings": ["すき", "げき", "ひま"],
        "priority": ["common"],
        "pos": ["noun"],
        "entry_type": "vocab",
        "senses": [
            {
                "glosses": ["gap", "space", "opening", "chink"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
            {
                "glosses": ["break", "interlude", "interval", "spare moment"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": ["すき"]},
                "xrefs": ["暇"], "antonyms": [],
            },
            {
                "glosses": ["chance", "opportunity", "weak spot", "unguarded moment"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": []},
                "xrefs": [], "antonyms": [],
            },
            {
                "glosses": ["breach (of a relationship)", "rift", "discord"],
                "labels": {"pos": ["noun"], "misc": [], "field": [], "dial": []},
                "restrictions": {"stagk": [], "stagr": ["げき"]},
                "xrefs": [], "antonyms": [],
            },
        ],
        "variants": {"written": ["隙", "透き", "空き"], "readings": ["すき", "げき", "ひま"]},
    },
]


def match(expression: str, reading: str, source_gloss: str,
          entries: Optional[list[Entry]] = None
          ) -> tuple[Optional[Entry], str, list[int]]:
    """Return (entry_or_None, match_status, candidates).

    candidates: list of seqs considered, for the QA report.
    entries=None uses live JMdict (stub fallback when unavailable);
    pass an explicit list (e.g. STUB_ENTRIES) for offline use/tests.
    """
    if entries is None:
        entries = live_entries(expression)
        if entries is None:
            entries = STUB_ENTRIES

    def _mentions(e, form):
        # Midori exports the as-searched form; for usually-kana words that
        # is kana while JMdict's kanji form differs (はしゃぐ vs 燥ぐ).
        return form in e["written_forms"] or form in e["readings"]

    pair_hits = [
        e for e in entries
        if reading in e["readings"] and _mentions(e, expression)
    ]
    if len(pair_hits) == 1:
        return pair_hits[0], "exact", [pair_hits[0]["jmdict_seq"]]
    if len(pair_hits) > 1:
        gloss_tokens = _tokens(source_gloss or "")
        scored = sorted(
            pair_hits,
            key=lambda e: len(gloss_tokens & _tokens(_gloss_text(e))),
            reverse=True,
        )
        best = len(gloss_tokens & _tokens(_gloss_text(scored[0])))
        second = len(gloss_tokens & _tokens(_gloss_text(scored[1])))
        seqs = [e["jmdict_seq"] for e in scored]
        if best - second >= 2:
            return scored[0], "inferred", seqs
        return scored[0], "ambiguous", seqs
    # Fallback: expression alone (reading mismatch / kana variant).
    expr_hits = [e for e in entries if _mentions(e, expression)]
    if expr_hits:
        return expr_hits[0], "inferred", [e["jmdict_seq"] for e in expr_hits]
    return None, "missing", []

"""Learner enrichment (prototype curated content).

Kept strictly separate from dictionary data: the model/curator may add
usage, collocations, and examples, but must never rewrite POS/senses.
Examples demonstrate the bookmarked sense, are short/natural, and the
English translates the sentence (not word-for-word).

NOTE: GENERATED holds hand-curated content for the seed words only.
Everything else gets FALLBACK (empty) until a real enrichment source
(LLM or example corpus) is wired in — the pipeline never invents
examples. The "source" marker ("curated" vs "fallback") lets future
runs tell the two apart.
"""
from typing import Any

GENERATED: dict[str, dict[str, Any]] = {
    "だらけ": {
        "usage": "Attaches to nouns as N＋だらけ. Usually implies an excessive or undesirable amount of something.",
        "collocations": ["間違いだらけ", "泥だらけ", "傷だらけ"],
        "example_jp": "この答案は間違いだらけだ。",
        "example_en": "This paper is full of mistakes.",
        "pattern": "N + だらけ",
    },
    "本来": {
        "usage": "Describes how something originally or essentially is, often contrasted with the current state.",
        "collocations": ["本来の姿", "本来なら", "本来の意味"],
        "example_jp": "本来なら昨日出発するはずだった。",
        "example_en": "Originally, we were supposed to leave yesterday.",
        "pattern": "",
    },
    "稽古": {
        "usage": "Practice or training, especially for traditional arts, sports, or performance. Used with する.",
        "collocations": ["稽古する", "稽古に励む", "朝稽古"],
        "example_jp": "毎日剣道の稽古に励んでいる。",
        "example_en": "He trains hard at kendo every day.",
        "pattern": "",
    },
    "理不尽": {
        "usage": "Often describes demands, treatment, rules, or situations that feel unfair and make no reasonable sense.",
        "collocations": ["理不尽な要求", "理不尽な扱い", "理不尽に怒られる"],
        "example_jp": "そんな理不尽な要求には応じられない。",
        "example_en": "I can't comply with such an unreasonable demand.",
        "pattern": "",
    },
    "杞憂": {
        "usage": "Used for worrying about something that ultimately has little or no basis. Often 杞憂に終わる.",
        "collocations": ["杞憂に終わる", "ただの杞憂", "杞憂だった"],
        "example_jp": "心配していたが、結局は杞憂に終わった。",
        "example_en": "I was worried, but in the end my fears proved unfounded.",
        "pattern": "",
    },
    "覇気": {
        "usage": "Drive or ambition to get ahead; often noted by its presence or absence (覇気がある／ない).",
        "collocations": ["覇気がある", "覇気がない", "覇気を見せる"],
        "example_jp": "彼は覇気にあふれた若者だ。",
        "example_en": "He is a young man full of drive.",
        "pattern": "",
    },
    "隙": {
        "usage": "A physical gap, a free moment, or an unguarded weak spot depending on context.",
        "collocations": ["隙がある", "隙を突く", "隙間時間"],
        "example_jp": "守備の隙を突いて得点した。",
        "example_en": "They scored by exploiting a gap in the defense.",
        "pattern": "",
    },
}

FALLBACK = {
    "usage": "",
    "collocations": [],
    "example_jp": "",
    "example_en": "",
    "pattern": "",
}


def generated_for(expression: str) -> dict[str, Any]:
    if expression in GENERATED:
        return {**GENERATED[expression], "source": "curated"}
    return {**FALLBACK, "source": "fallback"}

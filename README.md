# midori-anki

Turn Midori (Japanese dictionary, iOS) bookmark exports into rich Anki
flashcards with native deep links back into Midori.

Each card shows the headword with furigana, part of speech, numbered
JMdict senses, an example sentence, and expandable usage notes and
common patterns. Tapping the headword opens the word in Midori via
`midori://search?text=...`.

## Requirements

- Python 3.10+
- Anki (desktop or AnkiMobile) for importing the generated deck

## Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This pulls in `genanki` (deck generation) and `jamdict` +
`jamdict_data` (the JMdict dictionary database).

## Quickstart

1. Export your bookmarks from Midori as a quoted TSV file with three
   columns per row: expression, reading, gloss, e.g.

   ```
   "理不尽"	"りふじん"	"unreasonable, irrational, outrageous, absurd"
   ```

2. Generate the deck:

   ```
   python -m midori.cli --input ~/midori.tsv --outdir ~/decks/jp
   ```

3. Import `deck.apkg` into Anki (desktop: File → Import; AnkiMobile:
   open the file → Add to AnkiMobile).

The deck name defaults to the input file's stem (`midori.tsv` →
deck `midori`); override with `--deck-name 'My Deck'`. Without
`--outdir`, outputs go to `<input-stem>_anki/` next to the input file.

## What a card looks like

Front: kanji headword only (no furigana — that's what you're recalling).

Back: headword with furigana ruby, part of speech, numbered senses,
example sentence with translation, and expandable Usage / Common
patterns sections. Tapping the headword on the back opens it in Midori.

## Adding new bookmarks later

Just re-export the full bookmark list from Midori and rerun with
`--merge-from` pointing at your previous output:

```
python -m midori.cli --input ~/midori.tsv \
  --merge-from ~/decks/jp/enriched.json --outdir ~/decks/jp
```

Unchanged entries are reused as-is; only new or edited rows are
re-processed. Every note carries a stable ID derived from its JMdict
entry, so re-importing the regenerated `deck.apkg` updates existing
cards in place — review history and scheduling are preserved, and
reruns never create duplicates.

## Outputs

Each run produces, in the output directory:

- `deck.apkg` — the importable Anki deck
- `enriched.json` — canonical per-word data (dictionary + generated
  content), the input for `--merge-from` runs
- `anki_import.tsv` — the same data as a TSV for inspection/debugging
- `match_report.txt` — match quality summary plus the ambiguous and
  unmatched entries worth reviewing by hand

Card appearance lives in `templates/` (`front.html`, `back.html`,
`style.css`) and can be changed without touching the data pipeline.

## CLI reference

```
python -m midori.cli [--input BOOKMARKS] [--outdir DIR]
                           [--deck-name NAME] [--merge-from ENRICHED_JSON]
```

## Development

```
pip install -e . pytest
python -m pytest tests/ -q
```

Without network access the dictionary matcher falls back to a small
bundled stub so the test suite still runs offline.

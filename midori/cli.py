"""CLI: bookmarks.tsv -> enriched.json, anki_import.tsv, deck.apkg, match_report.txt."""
import argparse
import json
import os
from typing import Any, Optional

from . import enrich, jmdict
from .anki import build_record, make_model, write_apkg, write_report, write_tsv
from .jmdict import Entry
from .parse import Bookmark, parse_bookmarks

Record = dict[str, Any]

# Templates live next to the source tree, resolved from this file —
# never from the caller's working directory.
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)


def fingerprint(bm: Bookmark) -> str:
    """Stable identity for a seed row across runs."""
    return "\u0000".join([bm["expression"], bm["reading"], bm["source_gloss"]])


def load_prior(path: Optional[str]) -> dict[str, Record]:
    """Prior enriched.json keyed by fingerprint, for incremental runs."""
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {fingerprint(r): r for r in data}


def build_all(bookmarks: list[Bookmark], prior: dict[str, Record],
              entries: Optional[list[Entry]] = None) -> tuple[list[Record], int]:
    """Match + enrich, reusing prior records whose seed row is unchanged.

    Reused records keep their GUID and generated content verbatim, so
    reruns never duplicate or clobber notes Anki already has.
    entries=None uses live JMdict; pass a list for offline use/tests.
    """
    records = []
    reused = 0
    for bm in bookmarks:
        key = fingerprint(bm)
        if key in prior:
            records.append(prior[key])
            reused += 1
            continue
        entry, status, candidates = jmdict.match(
            bm["expression"], bm["reading"], bm["source_gloss"], entries=entries
        )
        lookup = jmdict.lookup_term_for(bm["expression"])
        gen = enrich.generated_for(bm["expression"])
        rec = build_record(bm, entry, status, lookup, gen, pattern=gen.get("pattern", ""))
        rec["candidates"] = candidates
        records.append(rec)
    return records, reused


def default_outdir(input_path: str) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(input_path)), base + "_anki")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="bookmarks.tsv")
    ap.add_argument("--outdir", default=None,
                    help="Defaults to <input-stem>_anki next to the input file.")
    ap.add_argument("--deck-name", default=None,
                    help="Defaults to the input file stem, e.g. bookmarks.tsv -> 'bookmarks'.")
    ap.add_argument("--merge-from", default=None, metavar="ENRICHED_JSON",
                    help="Reuse records from a previous enriched.json whose seed "
                         "row (expression/reading/gloss) is unchanged. New rows are "
                         "matched + enriched; reruns never duplicate notes.")
    args = ap.parse_args()

    if not args.deck_name:
        args.deck_name = os.path.splitext(os.path.basename(args.input))[0]
    if not args.outdir:
        args.outdir = default_outdir(args.input)

    os.makedirs(args.outdir, exist_ok=True)
    bookmarks = parse_bookmarks(args.input)
    prior = load_prior(args.merge_from)
    records, reused = build_all(bookmarks, prior)
    dropped = len(prior) - reused

    with open(os.path.join(args.outdir, "enriched.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    write_tsv(records, os.path.join(args.outdir, "anki_import.tsv"))
    model = make_model(
        os.path.join(TEMPLATE_DIR, "front.html"),
        os.path.join(TEMPLATE_DIR, "back.html"),
        os.path.join(TEMPLATE_DIR, "style.css"),
    )
    write_apkg(records, model, args.deck_name, os.path.join(args.outdir, "deck.apkg"))
    summary = write_report(records, os.path.join(args.outdir, "match_report.txt"))
    print(summary)
    print(f"wrote {len(records)} records to {args.outdir}/ "
          f"({reused} reused, {len(records) - reused} new)")
    if dropped > 0:
        print(f"note: {dropped} prior record(s) no longer in the input; "
              f"they are left out of this export (delete manually in Anki if desired).")


if __name__ == "__main__":
    main()

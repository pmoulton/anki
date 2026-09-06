"""Parse Midori bookmark exports as real quoted TSV."""
import csv

Bookmark = dict[str, str]


def parse_bookmarks(path: str) -> list[Bookmark]:
    """Return list of {expression, reading, source_gloss}.

    Uses the csv module with tab delimiter + UTF-8 so quoted fields,
    embedded tabs/newlines, and Japanese Unicode survive intact.
    """
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        for lineno, row in enumerate(reader, start=1):
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) < 3:
                raise ValueError(f"{path}:{lineno}: expected 3 tab fields, got {len(row)}")
            expression, reading, gloss = (c.strip() for c in row[:3])
            rows.append(
                {"expression": expression, "reading": reading, "source_gloss": gloss}
            )
    return rows

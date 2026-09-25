import json
from collections import Counter
from pathlib import Path


CANDIDATES_FILE = Path(
    "extracted/validated_candidates.json"
)

LOG_FILE = Path(
    "output/redaction_log.json"
)


def normalize(text):
    return " ".join(
        text.strip().lower().split()
    )


def physical_location(location):
    """
    Normalize a location.

    For table cells, merged Word cells can appear under
    several row/column coordinates. The table index and
    cell text are therefore used instead of treating every
    coordinate as a separate physical occurrence.
    """

    if location.get("type") == "table_cell":
        return (
            "table_cell",
            location.get("index"),
            location.get("text_key")
        )

    return (
        location.get("type"),
        location.get("index")
    )


def build_candidate_units(candidates):
    """
    Deduplicate repeated candidate coordinates.

    A candidate occurring several times because of a merged
    table cell is treated as one physical occurrence.
    """

    units = {}

    for candidate in candidates:

        location = candidate.get(
            "location",
            {}
        )

        pii_type = candidate.get(
            "type"
        )

        text = candidate.get(
            "text",
            ""
        )

        if location.get("type") == "table_cell":

            key = (
                "table_cell",
                location.get("index"),
                location.get("row"),
                normalize(text)
            )

        else:

            key = (
                location.get("type"),
                location.get("index"),
                pii_type,
                normalize(text)
            )

        if key not in units:
            units[key] = candidate

    return units


def build_log_units(log):
    """
    Build comparable units from successful redactions.
    """

    units = set()

    for item in log:

        location = item.get(
            "location",
            {}
        )

        pii_type = item.get(
            "type"
        )

        text = item.get(
            "original",
            ""
        )

        if location.get("type") == "table_cell":

            key = (
                "table_cell",
                location.get("index"),
                location.get("row"),
                normalize(text)
            )

        else:

            key = (
                location.get("type"),
                location.get("index"),
                pii_type,
                normalize(text)
            )

        units.add(key)

    return units


def main():

    with open(
        CANDIDATES_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        candidates = json.load(file)

    with open(
        LOG_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        log = json.load(file)

    candidate_units = build_candidate_units(
        candidates
    )

    log_units = build_log_units(
        log
    )

    missing_keys = [
        key
        for key in candidate_units
        if key not in log_units
    ]

    print()
    print(
        "REDACTION DIAGNOSTICS"
    )
    print(
        "=" * 70
    )

    print(
        f"Raw candidates       : {len(candidates)}"
    )

    print(
        f"Unique physical units: {len(candidate_units)}"
    )

    print(
        f"Successful units     : {len(log_units)}"
    )

    print(
        f"Missing units        : {len(missing_keys)}"
    )

    print()
    print(
        "MISSING BY TYPE"
    )
    print(
        "-" * 70
    )

    missing_by_type = Counter(
        candidate_units[key]["type"]
        for key in missing_keys
    )

    for pii_type, count in sorted(
        missing_by_type.items()
    ):
        print(
            f"{pii_type:<15} {count}"
        )

    print()
    print(
        "FIRST 50 MISSING UNITS"
    )
    print(
        "-" * 70
    )

    for key in missing_keys[:50]:

        item = candidate_units[key]

        print(
            f"\nType     : {item['type']}"
        )

        print(
            f"Text     : {item['text']}"
        )

        print(
            f"Location : {item['location']}"
        )


if __name__ == "__main__":
    main()
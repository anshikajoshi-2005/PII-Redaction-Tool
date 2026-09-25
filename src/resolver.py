import json
from pathlib import Path


INPUT_FILE = Path("extracted/pii_candidates.json")
OUTPUT_FILE = Path("extracted/validated_candidates.json")


TYPE_PRIORITY = {
    "EMAIL": 100,
    "PHONE": 95,
    "SSN": 100,
    "CREDIT_CARD": 100,
    "IP_ADDRESS": 100,
    "DATE_OF_BIRTH": 100,
    "ADDRESS": 90,
    "PERSON": 80,
    "COMPANY": 75
}


def candidate_length(candidate):
    return candidate["end"] - candidate["start"]


def same_location(a, b):
    location_a = a["location"]
    location_b = b["location"]

    if location_a["type"] != location_b["type"]:
        return False

    if location_a["index"] != location_b["index"]:
        return False

    if location_a["type"] == "table_cell":
        return (
            location_a.get("row") == location_b.get("row")
            and location_a.get("column") == location_b.get("column")
        )

    return True


def overlaps(a, b):
    if not same_location(a, b):
        return False

    return (
        a["start"] < b["end"]
        and b["start"] < a["end"]
    )


def candidate_score(candidate):
    confidence = candidate.get("confidence", 0)

    priority = TYPE_PRIORITY.get(
        candidate["type"],
        0
    )

    length_bonus = min(
        candidate_length(candidate) / 100,
        1
    )

    return (
        priority
        + confidence * 10
        + length_bonus
    )


def resolve_overlaps(candidates):
    """
    Keep the strongest candidate whenever two candidates
    overlap within the same text block.
    """

    sorted_candidates = sorted(
        candidates,
        key=lambda candidate: (
            candidate["location"]["type"],
            candidate["location"]["index"],
            candidate.get("row", -1),
            candidate.get("column", -1),
            candidate["start"]
        )
    )

    selected = []

    for candidate in sorted_candidates:

        conflicting = [
            existing
            for existing in selected
            if overlaps(candidate, existing)
        ]

        if not conflicting:
            selected.append(candidate)
            continue

        candidate_score_value = candidate_score(
            candidate
        )

        should_replace = True

        for existing in conflicting:

            existing_score_value = candidate_score(
                existing
            )

            if existing_score_value >= candidate_score_value:
                should_replace = False
                break

        if should_replace:

            selected = [
                existing
                for existing in selected
                if existing not in conflicting
            ]

            selected.append(candidate)

    return sorted(
        selected,
        key=lambda candidate: (
            candidate["location"]["type"],
            candidate["location"]["index"],
            candidate.get("row", -1),
            candidate.get("column", -1),
            candidate["start"]
        )
    )


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        candidates = json.load(file)

    print(
        f"Raw candidates: {len(candidates)}"
    )

    resolved = resolve_overlaps(
        candidates
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            resolved,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Resolved candidates: {len(resolved)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
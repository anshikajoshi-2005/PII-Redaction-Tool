import json
import sys
from pathlib import Path


INPUT_FILE = Path("extracted/pii_candidates.json")


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {INPUT_FILE}"
        )

    if len(sys.argv) < 2:
        print(
            "Usage: python -m src.show_candidates EMAIL"
        )
        return

    requested_type = sys.argv[1].upper()

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        candidates = json.load(file)

    matching = [
        candidate
        for candidate in candidates
        if candidate["type"] == requested_type
    ]

    print(
        f"\n{requested_type}: "
        f"{len(matching)} candidates\n"
    )

    seen = set()

    for candidate in matching:

        value = candidate["text"].strip()

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)

        print(
            f"{value}"
        )

        print(
            f"  source={candidate['source']}, "
            f"confidence={candidate['confidence']}, "
            f"location={candidate['location']}"
        )


if __name__ == "__main__":
    main()
import json
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("extracted/pii_candidates.json")
OUTPUT_FILE = Path("extracted/pii_review.txt")


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        candidates = json.load(file)

    grouped = defaultdict(list)

    for candidate in candidates:
        grouped[candidate["type"]].append(candidate)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        file.write("PII DETECTION REVIEW\n")
        file.write("=" * 80 + "\n\n")

        for pii_type in sorted(grouped):

            items = grouped[pii_type]

            file.write(
                f"{pii_type}: {len(items)} candidates\n"
            )

            file.write("-" * 80 + "\n")

            seen = set()

            unique_items = []

            for item in items:

                key = (
                    item["text"]
                    .strip()
                    .lower()
                )

                if key in seen:
                    continue

                seen.add(key)
                unique_items.append(item)

            file.write(
                f"Unique values: {len(unique_items)}\n\n"
            )

            for number, item in enumerate(
                unique_items[:100],
                start=1
            ):

                location = item["location"]

                file.write(
                    f"{number}. {item['text']}\n"
                )

                file.write(
                    f"   Source     : {item['source']}\n"
                )

                file.write(
                    f"   Confidence : {item['confidence']}\n"
                )

                file.write(
                    f"   Location   : {location}\n"
                )

                file.write("\n")

            if len(unique_items) > 100:
                file.write(
                    f"... "
                    f"{len(unique_items) - 100} more unique "
                    f"values not displayed.\n"
                )

            file.write("\n\n")

    print(
        f"Review file created: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
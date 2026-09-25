import json
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("extracted/pii_candidates.json")


def normalize(value):
    return " ".join(value.lower().split())


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

    print("\nPII CANDIDATE STATISTICS")
    print("=" * 70)

    for pii_type in sorted(grouped):

        items = grouped[pii_type]

        unique_values = {
            normalize(item["text"])
            for item in items
        }

        sources = defaultdict(int)

        for item in items:
            sources[item["source"]] += 1

        print(f"\n{pii_type}")
        print("-" * 70)
        print(f"Total occurrences : {len(items)}")
        print(f"Unique values     : {len(unique_values)}")

        print("Sources:")

        for source, count in sorted(
            sources.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {source}: {count}")


if __name__ == "__main__":
    main()
import json
import re
from pathlib import Path


INPUT_FILE = Path(
    "extracted/validated_candidates.json"
)

OUTPUT_FILE = Path(
    "extracted/replacement_map.json"
)


PERSON_NAMES = [
    "Arjun Mehta",
    "Rohan Sharma",
    "Neha Kapoor",
    "Aditi Verma",
    "Rahul Malhotra",
    "Priya Nair",
    "Karan Bhatia",
    "Ananya Gupta",
    "Vikram Singh",
    "Meera Joshi"
]


COMPANY_NAMES = [
    "Apex Manufacturing Limited",
    "Vertex Industrial Solutions Limited",
    "Northstar Technologies Private Limited",
    "BluePeak Industries Limited",
    "Summit Engineering Private Limited",
    "Evergreen Business Solutions Limited",
    "Prime Industrial Systems Limited",
    "Crestline Technologies Limited",
    "SilverOak Manufacturing Limited",
    "Pioneer Industrial Services Limited"
]


EMAIL_DOMAINS = [
    "example.com",
    "samplemail.com",
    "demo.example"
]


PHONE_NUMBERS = [
    "+91 9876543210",
    "+91 9123456780",
    "+91 9988776655",
    "+91 9012345678",
    "+91 9345678901"
]


ADDRESS_VALUES = [
    "42 Example Industrial Park, Pune - 411001, Maharashtra, India",
    "18 Sample Business Road, Mumbai - 400001, Maharashtra, India",
    "27 Demo Industrial Estate, Bengaluru - 560001, Karnataka, India",
    "55 Example Nagar, New Delhi - 110001, India",
    "12 Sample Road, Hyderabad - 500001, Telangana, India"
]


def normalize(value):
    return re.sub(
        r"\s+",
        " ",
        value.strip().lower()
    )


def generate_mapping(candidates):

    mapping = {}

    counters = {
        "PERSON": 0,
        "COMPANY": 0,
        "EMAIL": 0,
        "PHONE": 0,
        "ADDRESS": 0,
        "SSN": 0,
        "CREDIT_CARD": 0,
        "DATE_OF_BIRTH": 0,
        "IP_ADDRESS": 0
    }

    for candidate in candidates:

        pii_type = candidate["type"]
        original = candidate["text"]

        key = (
            pii_type,
            normalize(original)
        )

        if key in mapping:
            continue

        index = counters.get(
            pii_type,
            0
        )

        if pii_type == "PERSON":

            replacement = PERSON_NAMES[
                index % len(PERSON_NAMES)
            ]

        elif pii_type == "COMPANY":

            replacement = COMPANY_NAMES[
                index % len(COMPANY_NAMES)
            ]

        elif pii_type == "EMAIL":

            replacement = (
                f"contact{index + 1}"
                f"@{EMAIL_DOMAINS[index % len(EMAIL_DOMAINS)]}"
            )

        elif pii_type == "PHONE":

            replacement = PHONE_NUMBERS[
                index % len(PHONE_NUMBERS)
            ]

        elif pii_type == "ADDRESS":

            replacement = ADDRESS_VALUES[
                index % len(ADDRESS_VALUES)
            ]

        elif pii_type == "SSN":

            replacement = (
                f"9{index + 1:02d}-"
                f"45-{(index + 1000):04d}"
            )

        elif pii_type == "CREDIT_CARD":

            replacement = (
                "4111 1111 1111 1111"
            )

        elif pii_type == "DATE_OF_BIRTH":

            replacement = "15 January 1990"

        elif pii_type == "IP_ADDRESS":

            replacement = (
                f"192.0.2.{(index % 200) + 1}"
            )

        else:
            replacement = "[REDACTED]"

        mapping[key] = {
            "type": pii_type,
            "original": original,
            "replacement": replacement
        }

        counters[pii_type] = index + 1

    result = list(
        mapping.values()
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Replacement mappings: {len(result)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Validated candidates not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        candidates = json.load(file)

    generate_mapping(candidates)


if __name__ == "__main__":
    main()
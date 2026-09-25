import json
import ipaddress
import re
from pathlib import Path

import spacy

from src.patterns import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    SSN_PATTERN,
    CREDIT_CARD_PATTERN,
    IPV4_PATTERN,
    DOB_CONTEXT_PATTERN,
    PIN_CODE_PATTERN,
    ADDRESS_KEYWORDS,
    COMPANY_SUFFIX_PATTERN,
    COMPANY_CONTEXT_PATTERN,
    PERSON_CONTEXT_PATTERN,
    GENERIC_COMPANY_FALSE_POSITIVES,
    PERSON_EXCLUSION_TERMS,
    COMPANY_EXCLUSION_TERMS,
    LEGAL_OR_REGULATORY_TERMS
)


MODEL_NAME = "en_core_web_sm"


def load_nlp_model():
    """Load the spaCy NER model."""
    return spacy.load(MODEL_NAME)


def make_candidate(
    pii_type,
    text,
    start,
    end,
    source,
    confidence,
    location
):
    """Create a standardized PII candidate."""
    return {
        "type": pii_type,
        "text": text,
        "start": start,
        "end": end,
        "source": source,
        "confidence": round(confidence, 2),
        "location": location
    }


def is_valid_ipv4(value):
    """Validate an IPv4 address."""
    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


def luhn_check(number):
    """Validate a credit card number using the Luhn algorithm."""
    digits = re.sub(r"\D", "", number)

    if not 13 <= len(digits) <= 19:
        return False

    total = 0

    for index, digit in enumerate(reversed(digits)):
        value = int(digit)

        if index % 2 == 1:
            value *= 2

            if value > 9:
                value -= 9

        total += value

    return total % 10 == 0


def make_context(text, start, end, window=80):
    """Return surrounding text for contextual analysis."""
    context_start = max(0, start - window)
    context_end = min(len(text), end + window)

    return text[context_start:context_end]


def has_phone_context(text, start, end):
    """Check whether nearby text indicates a telephone number."""
    context = make_context(text, start, end).lower()

    keywords = [
        "telephone",
        "tel",
        "phone",
        "mobile",
        "contact",
        "fax"
    ]

    return any(keyword in context for keyword in keywords)


def detect_emails(text, location):
    """Detect email addresses."""
    candidates = []

    for match in EMAIL_PATTERN.finditer(text):
        candidates.append(
            make_candidate(
                "EMAIL",
                match.group(),
                match.start(),
                match.end(),
                "regex",
                0.99,
                location
            )
        )

    return candidates


def detect_phones(text, location):
    """Detect phone numbers with contextual filtering."""
    candidates = []

    for match in PHONE_PATTERN.finditer(text):
        value = match.group().strip()
        digits = re.sub(r"\D", "", value)

        if not 10 <= len(digits) <= 13:
            continue

        context_match = has_phone_context(
            text,
            match.start(),
            match.end()
        )

        if not context_match and len(digits) != 10:
            continue

        candidates.append(
            make_candidate(
                "PHONE",
                value,
                match.start(),
                match.end(),
                "regex",
                0.95 if context_match else 0.82,
                location
            )
        )

    return candidates


def detect_ssns(text, location):
    """Detect US Social Security Numbers."""
    candidates = []

    for match in SSN_PATTERN.finditer(text):
        candidates.append(
            make_candidate(
                "SSN",
                match.group(),
                match.start(),
                match.end(),
                "regex",
                0.99,
                location
            )
        )

    return candidates


def detect_credit_cards(text, location):
    """Detect and validate credit card numbers."""
    candidates = []

    for match in CREDIT_CARD_PATTERN.finditer(text):
        value = match.group().strip()

        if not luhn_check(value):
            continue

        candidates.append(
            make_candidate(
                "CREDIT_CARD",
                value,
                match.start(),
                match.end(),
                "regex+luhn",
                0.99,
                location
            )
        )

    return candidates


def detect_ipv4(text, location):
    """Detect valid IPv4 addresses."""
    candidates = []

    for match in IPV4_PATTERN.finditer(text):
        value = match.group()

        if not is_valid_ipv4(value):
            continue

        candidates.append(
            make_candidate(
                "IP_ADDRESS",
                value,
                match.start(),
                match.end(),
                "regex+validation",
                0.99,
                location
            )
        )

    return candidates


def detect_dobs(text, location):
    """Detect dates only when associated with DOB context."""
    candidates = []

    for match in DOB_CONTEXT_PATTERN.finditer(text):
        value = match.group(1)

        candidates.append(
            make_candidate(
                "DATE_OF_BIRTH",
                value,
                match.start(1),
                match.end(1),
                "context+regex",
                0.98,
                location
            )
        )

    return candidates


def looks_like_address(text):
    """Determine whether a text block contains strong address evidence."""

    if not text.strip():
        return False

    has_explicit_address_context = bool(
        ADDRESS_KEYWORDS.search(text)
    )

    has_pin_code = bool(
        PIN_CODE_PATTERN.search(text)
    )

    lower_text = text.lower()

    address_components = [
        "road",
        "street",
        "lane",
        "nagar",
        "society",
        "apartment",
        "flat",
        "village",
        "taluka",
        "district",
        "industrial estate",
        "business centre",
        "park",
        "phase",
        "sector"
    ]

    component_count = sum(
        component in lower_text
        for component in address_components
    )

    if has_explicit_address_context and (
        has_pin_code or component_count >= 1
    ):
        return True

    if has_pin_code and component_count >= 1:
        return True

    return False


def detect_addresses(text, location):
    """
    Detect physical addresses using explicit address context,
    address components and Indian PIN codes.
    """

    candidates = []

    if not looks_like_address(text):
        return candidates

    pin_matches = list(
        PIN_CODE_PATTERN.finditer(text)
    )

    if pin_matches:

        for pin_match in pin_matches:

            context_start = max(
                0,
                pin_match.start() - 250
            )

            context = text[
                context_start:pin_match.end()
            ]

            address_context = ADDRESS_KEYWORDS.search(
                context
            )

            if address_context:

                start = (
                    context_start +
                    address_context.start()
                )

            else:

                start = context_start

            address_text = text[
                start:pin_match.end()
            ].strip()

            if len(address_text) < 20:
                continue

            candidates.append(
                make_candidate(
                    "ADDRESS",
                    address_text,
                    start,
                    pin_match.end(),
                    "address+context+pin",
                    0.95,
                    location
                )
            )

    elif ADDRESS_KEYWORDS.search(text):

        match = ADDRESS_KEYWORDS.search(text)

        address_text = text[
            match.start():
        ].strip()

        if len(address_text) >= 25:

            candidates.append(
                make_candidate(
                    "ADDRESS",
                    address_text,
                    match.start(),
                    len(text),
                    "address+context",
                    0.82,
                    location
                )
            )

    return candidates


def is_valid_company_candidate(entity_text):
    """
    Validate whether a spaCy ORG entity looks like a plausible
    company, LLP, trust, foundation, or other organization.
    """

    value = re.sub(
        r"\s+",
        " ",
        entity_text.strip()
    )

    normalized = value.lower()

    if not value:
        return False

    if len(value) < 4:
        return False

    if "@" in value:
        return False

    if re.search(r"\d", value):
        return False

    # Exact exclusions.
    if normalized in COMPANY_EXCLUSION_TERMS:
        return False

    if normalized in LEGAL_OR_REGULATORY_TERMS:
        return False

    # ---------------------------------------------------------
    # Obvious non-company phrases
    # ---------------------------------------------------------

    blocked_phrases = [
        "offer",
        "anchor investor",
        "anchor investors",
        "registered office",
        "corporate office",
        "office",
        "registrar of companies",
        "indian accounting standards",
        "ind as",
        "care report",
        "promoter selling shareholders",
        "key managerial personnel",
        "group companies",
        "net proceeds",
        "supa facility",
        "calling and employment act",
        "practicing company",
        "goods and services tax",
        "risk factors",
        "floor price",
        "cap price",
        "reference rate",
        "website",
        "exchange",
        "exchanges",
        "mutual funds",
        "mutual fund",
        "bandra kurla complex",
        "bandra east",
        "appasaheb marathe marg",
        "waterloo industrial",
        "industrial park"
    ]

    if any(
        phrase in normalized
        for phrase in blocked_phrases
    ):
        return False

    words = value.split()

    if len(words) < 2:
        return False

    # ---------------------------------------------------------
    # Reject phrases made entirely from generic/legal words.
    # ---------------------------------------------------------

    generic_terms = {
        "board",
        "management",
        "directors",
        "promoters",
        "shareholders",
        "investors",
        "business",
        "company",
        "companies",
        "report",
        "website",
        "office",
        "risks",
        "limited",
        "private",
        "services",
        "systems",
        "solutions",
        "industries",
        "technology",
        "technologies"
    }

    meaningful_words = [
        word.lower().strip(".,()-&")
        for word in words
    ]

    if all(
        word in generic_terms
        for word in meaningful_words
    ):
        return False

    # ---------------------------------------------------------
    # Reject obvious fragments.
    # ---------------------------------------------------------

    if normalized in {
        "private limited",
        "limited",
        "india limited",
        "advisory private limited",
        "waterloo industrial",
        "pandit llp"
    }:
        return False

    # ---------------------------------------------------------
    # A legitimate organization should contain a meaningful
    # proper-name token.
    # ---------------------------------------------------------

    legal_suffixes = {
        "limited",
        "ltd",
        "private",
        "llp",
        "inc",
        "incorporated",
        "corporation",
        "corp",
        "industries",
        "technologies",
        "technology",
        "solutions",
        "services",
        "systems",
        "bank",
        "trust",
        "foundation"
    }

    meaningful_tokens = [
        word.strip(".,()-&")
        for word in words
        if word.lower().strip(".,()-&")
        not in legal_suffixes
    ]

    if not meaningful_tokens:
        return False

    # At least one meaningful token should contain alphabetic
    # characters.
    if not any(
        re.search(
            r"[A-Za-z]",
            word
        )
        for word in meaningful_tokens
    ):
        return False

    return True

def company_has_strong_context(text, start, end):
    """Check whether an organization appears in company-related context."""
    context = make_context(text, start, end, window=120)

    return bool(COMPANY_CONTEXT_PATTERN.search(context))

def is_valid_person_candidate(entity_text):
    """
    Validate whether a spaCy PERSON entity looks like an actual
    human name rather than a heading, location, legal term or
    other document phrase.
    """

    value = re.sub(
        r"\s+",
        " ",
        entity_text.strip()
    )

    normalized = value.lower()

    if not value:
        return False

    if normalized in PERSON_EXCLUSION_TERMS:
        return False

    if len(value) < 4:
        return False

    if "@" in value:
        return False

    if re.search(r"\d", value):
        return False

    words = value.split()

    if len(words) < 2 or len(words) > 5:
        return False

    if any(
        word.lower() in PERSON_EXCLUSION_TERMS
        for word in words
    ):
        return False

    if any(
        term in normalized
        for term in [
            "office",
            "price",
            "rate",
            "offer",
            "shareholder",
            "promoter",
            "director",
            "managerial",
            "taluka",
            "district",
            "website",
            "exchange",
            "branch",
            "company",
            "corporate"
        ]
    ):
        return False

    alphabetic_words = [
        word
        for word in words
        if re.search(r"[A-Za-z]", word)
    ]

    if len(alphabetic_words) < 2:
        return False

    return True

def detect_ner(text, location, nlp):
    """
    Detect PERSON and COMPANY candidates using spaCy NER
    followed by rule-based validation.
    """

    candidates = []

    doc = nlp(text)

    for entity in doc.ents:

        entity_text = entity.text.strip()

        if not entity_text:
            continue

        # -------------------------------------------------
        # PERSON
        # -------------------------------------------------

        if entity.label_ == "PERSON":

            if not is_valid_person_candidate(
                entity_text
            ):
                continue

            context = make_context(
                text,
                entity.start_char,
                entity.end_char,
                window=120
            )

            confidence = 0.82

            if PERSON_CONTEXT_PATTERN.search(
                context
            ):
                confidence = 0.95

            candidates.append(
                make_candidate(
                    "PERSON",
                    entity_text,
                    entity.start_char,
                    entity.end_char,
                    "spacy_ner",
                    confidence,
                    location
                )
            )

        # -------------------------------------------------
        # COMPANY
        # -------------------------------------------------

        elif entity.label_ == "ORG":

            if not is_valid_company_candidate(
                entity_text
            ):
                continue

            normalized = re.sub(
                r"\s+",
                " ",
                entity_text.lower().strip()
            )

            if normalized in COMPANY_EXCLUSION_TERMS:
                continue

            if any(
                term in normalized
                for term in LEGAL_OR_REGULATORY_TERMS
            ):
                continue

            has_suffix = bool(
                COMPANY_SUFFIX_PATTERN.search(
                    entity_text
                )
            )

            has_company_context = (
                company_has_strong_context(
                    text,
                    entity.start_char,
                    entity.end_char
                )
            )

            # Require at least one strong signal.
            if not has_suffix and not has_company_context:
                continue

            # Avoid entities that are primarily regulatory/legal.
            if not has_suffix:
                context = make_context(
                    text,
                    entity.start_char,
                    entity.end_char,
                    window=120
                )

                if not re.search(
                    r"\b(?:subsidiary|"
                    r"associate\s+company|"
                    r"group\s+company|"
                    r"promoter\s+company|"
                    r"company\s+named|"
                    r"company\s+known\s+as)\b",
                    context,
                    re.IGNORECASE
                ):
                    continue

            if has_suffix and has_company_context:
                confidence = 0.97
            elif has_suffix:
                confidence = 0.92
            else:
                confidence = 0.88

            candidates.append(
                make_candidate(
                    "COMPANY",
                    entity_text,
                    entity.start_char,
                    entity.end_char,
                    "spacy_ner+validation",
                    confidence,
                    location
                )
            )

    return candidates


def detect_companies_by_pattern(text, location):
    """
    Detect company names using explicit legal/company suffixes.

    High-precision detector:
    - Requires a meaningful proper-name component.
    - Rejects generic fragments such as "Private Limited".
    - Rejects location/address phrases.
    """

    candidates = []

    pattern = re.compile(
        r"\b"
        r"(?:"
        r"[A-Z][A-Za-z0-9&.'()-]*\s+"
        r"){1,7}"
        r"(?:"
        r"Limited|Ltd\.?|"
        r"Private Limited|Pvt\.?\s*Ltd\.?|"
        r"LLP|"
        r"Corporation|Corp\.?|"
        r"Industries|"
        r"Technologies|"
        r"Technology|"
        r"Trust|"
        r"Foundation"
        r")"
        r"\b"
    )

    for match in pattern.finditer(text):

        value = re.sub(
            r"\s+",
            " ",
            match.group().strip()
        )

        normalized = value.lower()

        if normalized in COMPANY_EXCLUSION_TERMS:
            continue

        if normalized in {
            "private limited",
            "limited",
            "india limited",
            "advisory private limited"
        }:
            continue

        if any(
            term in normalized
            for term in LEGAL_OR_REGULATORY_TERMS
        ):
            continue

        # Reject address/location phrases.
        if any(
            term in normalized
            for term in [
                "industrial park",
                "business centre",
                "business center",
                "bandra",
                "marg",
                "road",
                "street",
                "lane",
                "village",
                "taluka",
                "district",
                "pune",
                "mumbai"
            ]
        ):
            continue

        words = value.split()

        if len(words) < 2:
            continue

        # Remove legal suffix words.
        legal_suffixes = {
            "limited",
            "ltd",
            "private",
            "llp",
            "corporation",
            "corp",
            "industries",
            "technologies",
            "technology",
            "trust",
            "foundation"
        }

        meaningful_words = [
            word.strip(".,()-&")
            for word in words
            if word.lower().strip(".,()-&")
            not in legal_suffixes
        ]

        if not meaningful_words:
            continue

        # There must be at least one meaningful proper-name
        # component before the legal suffix.
        if not any(
            re.match(
                r"^[A-Z][A-Za-z0-9&.'()-]*$",
                word
            )
            for word in meaningful_words
        ):
            continue

        candidates.append(
            make_candidate(
                "COMPANY",
                value,
                match.start(),
                match.end(),
                "company_suffix",
                0.94,
                location
            )
        )

    return candidates

def deduplicate_candidates(candidates):
    """Remove exact duplicate candidates."""
    unique = {}
    result = []

    for candidate in candidates:
        key = (
            candidate["type"],
            candidate["text"].strip().lower(),
            candidate["start"],
            candidate["end"],
            candidate["location"]["type"],
            candidate["location"]["index"],
            candidate["location"].get("row"),
            candidate["location"].get("column")
        )

        if key not in unique:
            unique[key] = True
            result.append(candidate)

    return result


def process_block(text, location, nlp):
    """Run all detectors on a single text block."""
    if not text.strip():
        return []

    candidates = []

    candidates.extend(
        detect_emails(text, location)
    )

    candidates.extend(
        detect_phones(text, location)
    )

    candidates.extend(
        detect_ssns(text, location)
    )

    candidates.extend(
        detect_credit_cards(text, location)
    )

    candidates.extend(
        detect_ipv4(text, location)
    )

    candidates.extend(
        detect_dobs(text, location)
    )

    candidates.extend(
        detect_addresses(text, location)
    )

    candidates.extend(
        detect_ner(text, location, nlp)
    )

    candidates.extend(
        detect_companies_by_pattern(text, location)
    )

    return deduplicate_candidates(candidates)


def process_document_content(content, nlp):
    """Process paragraphs and table cells."""
    all_candidates = []

    for paragraph in content["paragraphs"]:
        text = paragraph["text"]

        location = {
            "type": "paragraph",
            "index": paragraph["index"]
        }

        all_candidates.extend(
            process_block(text, location, nlp)
        )

    for table in content["tables"]:
        table_index = table["table_index"]

        for row in table["rows"]:
            for cell in row:
                text = cell["text"]

                if not text.strip():
                    continue

                location = {
                    "type": "table_cell",
                    "index": table_index,
                    "row": cell["row"],
                    "column": cell["column"]
                }

                all_candidates.extend(
                    process_block(text, location, nlp)
                )

    return deduplicate_candidates(all_candidates)


def main():
    input_file = Path("extracted/document_content.json")
    output_file = Path("extracted/pii_candidates.json")

    if not input_file.exists():
        raise FileNotFoundError(
            f"Extracted document not found: {input_file}"
        )

    print("Loading extracted document...")

    with open(input_file, "r", encoding="utf-8") as file:
        content = json.load(file)

    print("Loading spaCy model...")
    nlp = load_nlp_model()

    print("Running PII detection...")

    candidates = process_document_content(
        content,
        nlp
    )

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            candidates,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nDetection completed.")
    print(f"Total candidates found: {len(candidates)}")
    print(f"Results saved to: {output_file}")

    counts = {}

    for candidate in candidates:
        pii_type = candidate["type"]
        counts[pii_type] = counts.get(
            pii_type,
            0
        ) + 1

    print("\nDetected PII by type:")

    for pii_type, count in sorted(counts.items()):
        print(f"{pii_type}: {count}")


if __name__ == "__main__":
    main()
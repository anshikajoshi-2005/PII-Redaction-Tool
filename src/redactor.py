import json
import re
from pathlib import Path
from docx import Document

INPUT_DOCX = Path("input/Red Herring Prospectus.docx")
CANDIDATES_FILE = Path("extracted/validated_candidates.json")
REPLACEMENT_FILE = Path("extracted/replacement_map.json")
OUTPUT_DOCX = Path("output/redacted_prospectus.docx")
LOG_FILE = Path("output/redaction_log.json")


def normalize_text(text):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def load_candidates():
    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {CANDIDATES_FILE}"
        )

    with open(CANDIDATES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def load_replacement_map():
    if not REPLACEMENT_FILE.exists():
        raise FileNotFoundError(
            f"Replacement map not found: {REPLACEMENT_FILE}"
        )

    with open(REPLACEMENT_FILE, "r", encoding="utf-8") as file:
        mappings = json.load(file)

    replacement_map = {}

    for item in mappings:
        key = (
            item["type"],
            normalize_text(item["original"])
        )
        replacement_map[key] = item["replacement"]

    return replacement_map


def get_candidate_replacement(candidate, replacement_map):
    key = (
        candidate["type"],
        normalize_text(candidate["text"])
    )
    return replacement_map.get(key)


def get_cell_identity(cell):
    return cell._tc.getroottree().getpath(cell._tc)


def find_all_occurrences(full_text, target):
    """
    Find every occurrence of target in full_text.

    Matching is attempted using:
    1. Exact match
    2. Case-insensitive match
    3. Whitespace-tolerant match
    """

    if not full_text or not target:
        return []

    occurrences = []

    # ---------------------------------------------------------
    # Exact matching
    # ---------------------------------------------------------

    start = 0

    while True:
        position = full_text.find(target, start)

        if position == -1:
            break

        occurrences.append(
            (
                position,
                position + len(target)
            )
        )

        start = position + len(target)

    if occurrences:
        return occurrences

    # ---------------------------------------------------------
    # Case-insensitive matching
    # ---------------------------------------------------------

    pattern = re.escape(target)

    match = re.search(
        pattern,
        full_text,
        flags=re.IGNORECASE
    )

    if match:
        # Find all case-insensitive occurrences
        regex = re.compile(
            pattern,
            flags=re.IGNORECASE
        )

        return [
            (match.start(), match.end())
            for match in regex.finditer(full_text)
        ]

    # ---------------------------------------------------------
    # Whitespace-tolerant matching
    # ---------------------------------------------------------

    whitespace_pattern = re.escape(target)

    whitespace_pattern = re.sub(
        r"\\\s+",
        r"\\s+",
        whitespace_pattern
    )

    regex = re.compile(
        whitespace_pattern,
        flags=re.IGNORECASE
    )

    return [
        (match.start(), match.end())
        for match in regex.finditer(full_text)
    ]


def resolve_replacements(
    candidates,
    full_text,
    replacement_map
):
    """
    Find every valid occurrence of every candidate in the
    actual paragraph/cell text.

    Longer candidates are processed first so that a larger
    PII entity gets priority over a smaller overlapping one.
    """

    possible_replacements = []

    # ---------------------------------------------------------
    # Process longer candidates first
    # ---------------------------------------------------------

    ordered_candidates = sorted(
        candidates,
        key=lambda candidate: (
            -len(candidate.get("text", "")),
            candidate.get("type", "")
        )
    )

    for candidate in ordered_candidates:

        candidate_text = candidate.get("text", "")

        if not candidate_text:
            continue

        replacement = get_candidate_replacement(
            candidate,
            replacement_map
        )

        if replacement is None:
            continue

        occurrences = find_all_occurrences(
            full_text,
            candidate_text
        )

        for start, end in occurrences:

            possible_replacements.append(
                {
                    "type": candidate["type"],
                    "original": candidate_text,
                    "replacement": replacement,
                    "start": start,
                    "end": end,
                    "source": candidate.get("source"),
                    "confidence": candidate.get("confidence")
                }
            )

    # ---------------------------------------------------------
    # Resolve overlapping matches
    # ---------------------------------------------------------

    possible_replacements.sort(
        key=lambda item: (
            item["start"],
            -(item["end"] - item["start"])
        )
    )

    resolved = []
    used_spans = []

    for item in possible_replacements:

        start = item["start"]
        end = item["end"]

        overlap = any(
            start < existing_end
            and existing_start < end
            for existing_start, existing_end in used_spans
        )

        if overlap:
            continue

        used_spans.append(
            (start, end)
        )

        resolved.append(item)

    return resolved


def transform_run_text(runs, replacements):
    """
    Apply replacements while preserving the existing Word
    run structure as much as possible.

    PII spanning multiple runs is supported.
    """

    if not runs or not replacements:
        return False

    run_ranges = []
    current_position = 0

    for run in runs:

        text = run.text or ""

        start = current_position
        end = start + len(text)

        run_ranges.append(
            (start, end)
        )

        current_position = end

    replacement_by_start = {
        item["start"]: item
        for item in replacements
    }

    changed = False

    def replacement_covering(position):

        for item in replacements:

            if (
                item["start"]
                <= position
                < item["end"]
            ):
                return item

        return None

    for run_index, run in enumerate(runs):

        original_text = run.text or ""

        if not original_text:
            continue

        run_start, run_end = run_ranges[
            run_index
        ]

        new_text = []

        for local_index, character in enumerate(
            original_text
        ):

            global_position = (
                run_start + local_index
            )

            replacement = replacement_by_start.get(
                global_position
            )

            if replacement is not None:

                new_text.append(
                    replacement["replacement"]
                )

                changed = True
                continue

            covered_by = replacement_covering(
                global_position
            )

            if covered_by is not None:

                changed = True
                continue

            new_text.append(character)

        new_value = "".join(new_text)

        if new_value != original_text:
            run.text = new_value

    return changed
def transform_cross_paragraph(
    paragraphs,
    candidate,
    replacement
):
    """
    Replace a candidate whose text spans multiple paragraphs.

    The candidate text is matched against the combined paragraph
    text, while the actual replacement is applied across the
    affected paragraph runs.
    """

    if not paragraphs or not candidate:
        return False

    candidate_text = candidate.get("text", "")

    if not candidate_text:
        return False

    paragraph_texts = [
        "".join(
            run.text or ""
            for run in paragraph.runs
        )
        for paragraph in paragraphs
    ]

    combined_text = "\n".join(
        paragraph_texts
    )

    occurrences = find_all_occurrences(
        combined_text,
        candidate_text
    )

    if not occurrences:
        return False

    start, end = occurrences[0]

    # Build character ranges for each paragraph.
    paragraph_ranges = []

    position = 0

    for paragraph_text in paragraph_texts:

        paragraph_start = position
        paragraph_end = (
            paragraph_start
            + len(paragraph_text)
        )

        paragraph_ranges.append(
            (
                paragraph_start,
                paragraph_end
            )
        )

        position = paragraph_end + 1

    changed = False

    for paragraph_index, paragraph in enumerate(
        paragraphs
    ):

        paragraph_start, paragraph_end = (
            paragraph_ranges[paragraph_index]
        )

        overlap_start = max(
            start,
            paragraph_start
        )

        overlap_end = min(
            end,
            paragraph_end
        )

        if overlap_start >= overlap_end:
            continue

        local_start = (
            overlap_start
            - paragraph_start
        )

        local_end = (
            overlap_end
            - paragraph_start
        )

        runs = paragraph.runs

        if not runs:
            continue

        run_ranges = []
        current_position = 0

        for run in runs:

            text = run.text or ""

            run_start = current_position
            run_end = (
                run_start
                + len(text)
            )

            run_ranges.append(
                (
                    run_start,
                    run_end
                )
            )

            current_position = run_end

        inserted = False

        for run_index, run in enumerate(runs):

            original_text = run.text or ""

            if not original_text:
                continue

            run_start, run_end = (
                run_ranges[run_index]
            )

            new_text = []

            for local_index, character in enumerate(
                original_text
            ):

                if (
                    local_start
                    <= run_start + local_index
                    < local_end
                ):

                    if not inserted:
                        new_text.append(
                            replacement
                        )
                        inserted = True

                    changed = True

                else:
                    new_text.append(
                        character
                    )

            new_value = "".join(
                new_text
            )

            if new_value != original_text:
                run.text = new_value

    return changed

def process_text_container(
    paragraphs,
    candidates,
    replacement_map,
    location
):
    """
    Process all paragraphs belonging to a physical document
    container.

    This is used for both normal paragraphs and table cells.
    """

    all_changes = []

    if not candidates:
        return all_changes

    for paragraph in paragraphs:

        if not paragraph.runs:
            continue

        full_text = "".join(
            run.text or ""
            for run in paragraph.runs
        )

        if not full_text:
            continue

        replacements = resolve_replacements(
            candidates,
            full_text,
            replacement_map
        )

        if not replacements:
            continue

        changed = transform_run_text(
            paragraph.runs,
            replacements
        )

        if not changed:
            continue

        for item in replacements:

            log_item = item.copy()

            log_item["location"] = location

            all_changes.append(
                log_item
            )
            # ---------------------------------------------------------
    # Handle candidates spanning multiple paragraphs.
    # ---------------------------------------------------------

    processed_keys = {
        (
            item.get("type"),
            normalize_text(
                item.get("original", "")
            )
        )
        for item in all_changes
    }

    combined_text = "\n".join(
        "".join(
            run.text or ""
            for run in paragraph.runs
        )
        for paragraph in paragraphs
    )

    for candidate in candidates:

        candidate_key = (
            candidate.get("type"),
            normalize_text(
                candidate.get("text", "")
            )
        )

        if candidate_key in processed_keys:
            continue

        candidate_text = candidate.get(
            "text",
            ""
        )

        if not candidate_text:
            continue

        replacement = get_candidate_replacement(
            candidate,
            replacement_map
        )

        if replacement is None:
            continue

        occurrences = find_all_occurrences(
            combined_text,
            candidate_text
        )

        if not occurrences:
            continue

        changed = transform_cross_paragraph(
            paragraphs,
            candidate,
            replacement
        )

        if not changed:
            continue

        start, end = occurrences[0]

        all_changes.append(
            {
                "type": candidate["type"],
                "original": candidate_text,
                "replacement": replacement,
                "start": start,
                "end": end,
                "source": candidate.get(
                    "source"
                ),
                "confidence": candidate.get(
                    "confidence"
                ),
                "location": location
            }
        )

    return all_changes

def process_paragraph(
    paragraph,
    candidates,
    replacement_map,
    location
):
    """
    Process a paragraph and replace all validated PII occurrences.
    """

    if not paragraph.runs:
        return [], False

    full_text = "".join(
        run.text or ""
        for run in paragraph.runs
    )

    if not full_text:
        return [], False

    resolved = []
    used_spans = []

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -len(candidate.get("text", ""))
        )
    )

    for candidate in ordered:

        candidate_text = candidate.get(
            "text",
            ""
        )

        if not candidate_text:
            continue

        replacement = get_candidate_replacement(
            candidate,
            replacement_map
        )

        if replacement is None:
            continue

        matches = []

        # Exact matches
        search_start = 0

        while True:
            start = full_text.find(
                candidate_text,
                search_start
            )

            if start == -1:
                break

            end = start + len(candidate_text)

            matches.append(
                (start, end)
            )

            search_start = start + 1

        # Case-insensitive matches
        if not matches:
            lower_text = full_text.lower()
            lower_candidate = candidate_text.lower()

            search_start = 0

            while True:
                start = lower_text.find(
                    lower_candidate,
                    search_start
                )

                if start == -1:
                    break

                end = start + len(candidate_text)

                matches.append(
                    (start, end)
                )

                search_start = start + 1

        # Whitespace-tolerant matching
        if not matches:
            pattern = re.escape(
                candidate_text
            )

            pattern = re.sub(
                r"\\\s+",
                r"\\s+",
                pattern
            )

            for match in re.finditer(
                pattern,
                full_text,
                flags=re.IGNORECASE
            ):
                matches.append(
                    (
                        match.start(),
                        match.end()
                    )
                )

        # Add every non-overlapping occurrence
        for start, end in matches:

            overlap = any(
                start < existing_end
                and existing_start < end
                for existing_start, existing_end
                in used_spans
            )

            if overlap:
                continue

            used_spans.append(
                (
                    start,
                    end
                )
            )

            resolved.append(
                {
                    "type": candidate["type"],
                    "original": candidate["text"],
                    "replacement": replacement,
                    "start": start,
                    "end": end,
                    "source": candidate.get(
                        "source"
                    ),
                    "confidence": candidate.get(
                        "confidence"
                    )
                }
            )

    if not resolved:
        return [], False

    resolved.sort(
        key=lambda item: item["start"]
    )

    changed = transform_run_text(
        paragraph.runs,
        resolved
    )

    for item in resolved:
        item["location"] = location

    return resolved, changed
def process_document_paragraphs(
    document,
    candidates_by_location,
    replacement_map,
    log
):
    """
    Process normal body paragraphs.
    """

    for paragraph_index, paragraph in enumerate(
        document.paragraphs
    ):

        key = (
            "paragraph",
            paragraph_index
        )

        candidates = candidates_by_location.get(
            key,
            []
        )

        if not candidates:
            continue

        location = {
            "type": "paragraph",
            "index": paragraph_index
        }

        changes = process_text_container(
            [paragraph],
            candidates,
            replacement_map,
            location
        )

        if changes:
            log.extend(changes)


def process_document_tables(
    document,
    candidates_by_location,
    replacement_map,
    log
):
    """
    Process each physical table cell exactly once.

    Merged Word cells can appear at multiple row/column
    coordinates. The underlying XML identity is used to
    prevent duplicate processing.
    """

    processed_cells = set()

    for table_index, table in enumerate(
        document.tables
    ):

        for row_index, row in enumerate(
            table.rows
        ):

            for column_index, cell in enumerate(
                row.cells
            ):

                cell_identity = get_cell_identity(
                    cell
                )

                if cell_identity in processed_cells:
                    continue

                processed_cells.add(
                    cell_identity
                )

                # -------------------------------------------------
                # Find every candidate whose stored coordinate
                # belongs to this physical cell.
                # -------------------------------------------------

                cell_candidates = []

                for key, candidates in (
                    candidates_by_location.items()
                ):

                    if len(key) != 4:
                        continue

                    if key[0] != "table_cell":
                        continue

                    candidate_table = key[1]
                    candidate_row = key[2]
                    candidate_column = key[3]

                    if candidate_table != table_index:
                        continue

                    try:

                        candidate_cell = (
                            table.rows[
                                candidate_row
                            ].cells[
                                candidate_column
                            ]
                        )

                    except (
                        IndexError,
                        KeyError
                    ):
                        continue

                    if get_cell_identity(
                        candidate_cell
                    ) != cell_identity:
                        continue

                    cell_candidates.extend(
                        candidates
                    )

                if not cell_candidates:
                    continue

                # -------------------------------------------------
                # Remove duplicate candidates caused by merged
                # cell coordinates.
                # -------------------------------------------------

                unique_candidates = []

                seen = set()

                for candidate in cell_candidates:

                    key = (
                        candidate.get("type"),
                        normalize_text(
                            candidate.get("text", "")
                        )
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    unique_candidates.append(
                        candidate
                    )

                location = {
                    "type": "table_cell",
                    "index": table_index,
                    "row": row_index,
                    "column": column_index
                }

                changes = process_text_container(
                    cell.paragraphs,
                    unique_candidates,
                    replacement_map,
                    location
                )

                if changes:
                    log.extend(changes)


def save_log(log):

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        LOG_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            log,
            file,
            ensure_ascii=False,
            indent=2
        )


def print_summary(
    candidates,
    log
):

    detected_by_type = {}
    redacted_by_type = {}

    for candidate in candidates:

        pii_type = candidate["type"]

        detected_by_type[pii_type] = (
            detected_by_type.get(
                pii_type,
                0
            ) + 1
        )

    for item in log:

        pii_type = item["type"]

        redacted_by_type[pii_type] = (
            redacted_by_type.get(
                pii_type,
                0
            ) + 1
        )

    print()
    print(
        "PII REDACTION SUMMARY"
    )
    print(
        "=" * 60
    )

    all_types = sorted(
        set(detected_by_type)
        | set(redacted_by_type)
    )

    for pii_type in all_types:

        detected = detected_by_type.get(
            pii_type,
            0
        )

        redacted = redacted_by_type.get(
            pii_type,
            0
        )

        print(
            f"{pii_type:<15}"
            f" detected={detected:<6}"
            f" redacted={redacted}"
        )

    print(
        "-" * 60
    )

    print(
        f"Total candidates : {len(candidates)}"
    )

    print(
        f"Total redacted   : {len(log)}"
    )


def main():

    print(
        "Loading validated candidates..."
    )

    candidates = load_candidates()

    print(
        f"Loaded {len(candidates)} candidates."
    )

    print(
        "Loading replacement map..."
    )

    replacement_map = load_replacement_map()

    print(
        f"Loaded {len(replacement_map)} mappings."
    )

    if not INPUT_DOCX.exists():
        raise FileNotFoundError(
            f"Input document not found: {INPUT_DOCX}"
        )

    print(
        "Loading original DOCX..."
    )

    document = Document(
        str(INPUT_DOCX)
    )

    # ---------------------------------------------------------
    # Group candidates by their original location.
    # ---------------------------------------------------------

    candidates_by_location = {}

    for candidate in candidates:

        location = candidate.get(
            "location"
        )

        if not location:
            continue

        location_type = location.get(
            "type"
        )

        index = location.get(
            "index"
        )

        if location_type == "table_cell":

            key = (
                "table_cell",
                index,
                location.get("row"),
                location.get("column")
            )

        else:

            key = (
                location_type,
                index
            )

        candidates_by_location.setdefault(
            key,
            []
        ).append(candidate)

    redaction_log = []

    print(
        "Processing paragraphs..."
    )

    process_document_paragraphs(
        document,
        candidates_by_location,
        replacement_map,
        redaction_log
    )

    print(
        "Processing tables..."
    )

    process_document_tables(
        document,
        candidates_by_location,
        replacement_map,
        redaction_log
    )

    OUTPUT_DOCX.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "Saving redacted document..."
    )

    document.save(
        str(OUTPUT_DOCX)
    )

    save_log(
        redaction_log
    )

    print_summary(
        candidates,
        redaction_log
    )

    print()

    print(
        f"Redacted document: {OUTPUT_DOCX}"
    )

    print(
        f"Redaction log: {LOG_FILE}"
    )


if __name__ == "__main__":
    main()
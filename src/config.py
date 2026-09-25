from pathlib import Path


INPUT_DOCX = Path(
    "input/Red Herring Prospectus.docx"
)

OUTPUT_DOCX = Path(
    "output/redacted_prospectus.docx"
)

VALIDATED_CANDIDATES = Path(
    "extracted/validated_candidates.json"
)

REPLACEMENT_MAP = Path(
    "extracted/replacement_map.json"
)

REDACTION_LOG = Path(
    "output/redaction_log.json"
)
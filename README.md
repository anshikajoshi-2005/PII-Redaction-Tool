# PII Redaction Tool
A Python-based document processing tool for detecting, validating, replacing, and redacting Personally Identifiable Information (PII) from Microsoft Word (`.docx`) documents.

The project processes a source document, identifies potential PII using a combination of regular expressions, rule-based patterns, contextual detection, and spaCy Named Entity Recognition (NER), validates the detected candidates, generates replacement values, and produces a redacted DOCX document along with a detailed redaction log.

---
## 1. Project Objective

The objective of this project is to automate the identification and redaction of sensitive information present in large Word documents.

The tool is designed to:

- Detect different categories of PII from DOCX documents.
- Combine multiple detection techniques for better coverage.
- Validate detected candidates before redaction.
- Generate consistent replacement values for validated PII.
- Preserve the original document structure as much as possible.
- Handle PII appearing across multiple runs and paragraphs.
- Process PII present inside tables.
- Maintain a detailed log of performed redactions.
- Provide diagnostic information for verifying redaction coverage.
- Include automated unit tests for the detection components.

---

## 2. PII Categories

The current implementation detects the following PII categories:

| PII Type | Description |
|----------|-------------|
| PERSON | Names of individuals |
| COMPANY | Company and organization names |
| EMAIL | Email addresses |
| PHONE | Telephone/mobile numbers |
| ADDRESS | Postal and residential/business addresses |

---

## 3. Key Features

### Multi-method PII Detection

The detection pipeline combines:

- spaCy Named Entity Recognition
- Regular expressions
- Company suffix patterns
- Address patterns
- Context-based detection
- PIN-code based address detection

This allows the system to identify PII using both linguistic and rule-based approaches.

### Candidate Validation

Detected candidates are passed through a validation and resolution stage before they are used for redaction.

This helps remove invalid or unsuitable candidates and produces a validated candidate set.

### Replacement Generation

Validated PII values are mapped to replacement values.

The replacement system maintains consistency so that repeated occurrences of the same validated PII value can be replaced using the corresponding generated value.

### DOCX Redaction

The tool modifies the Word document while processing:

- Normal paragraphs
- Multiple text runs
- Table cells
- Multiple paragraphs within table cells
- PII spanning across paragraph boundaries

### Redaction Logging

Every successful redaction is recorded in a JSON log containing information such as:

- PII type
- Original value
- Replacement value
- Position information
- Detection source
- Confidence
- Document location

### Diagnostics

The project includes a diagnostic module to compare validated candidates with successfully redacted physical document units.

This helps verify that detected PII was actually processed by the redaction stage.

### Automated Testing

The project includes unit tests for the detector components using pytest.

Current test result:

```text
14 passed

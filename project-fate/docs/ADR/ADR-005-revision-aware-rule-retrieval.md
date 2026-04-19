# ADR-005: Use Revision-Aware Metadata for Rule Retrieval

## Context

JR Pass rules can change over time. Eligibility, pricing references, train coverage, reservation requirements, and FAQ wording may all be revised after publication.

If chunks are indexed without revision-aware metadata, retrieval may return text from different document versions without signaling which rule is current. That creates three risks:

- outdated rule text may be cited as current
- conflicting chunks may appear equally valid during retrieval
- answer generation may not detect rule-version ambiguity

Because this system is designed for official-rule consultation, document recency and version traceability are essential.

## Decision

Every indexed chunk will carry revision-aware metadata, including:

- `source_url`
- `pass_name`
- `rule_category`
- `revision_date`
- `document_status`

Retrieval and reranking should prefer the most recent active rule content when multiple relevant chunks exist. If conflicting revisions are detected, the response should surface a warning instead of silently choosing one.

## Status

Accepted

## Consequences

### Positive

- reduces the risk of citing obsolete rules
- improves citation traceability
- supports revision conflict detection
- strengthens trust in compliance-oriented answers

### Negative

- increases ingestion and metadata-management complexity
- requires reliable extraction of revision dates and document status

### Follow-up implications

- the vector schema and ETL pipeline must preserve revision fields
- evaluation should include cases where multiple revisions exist for the same rule

# ADR-003: Restrict First Release Corpus to Official JR Pass Documents

## Context

The project is a `JR Pass Official Rules & Compliance RAG Consultation System`. Its primary goal is to answer eligibility, restriction, and rule-compliance questions with traceable evidence.

If the first release ingests unofficial blogs, travel forums, or derivative summaries, the system may retrieve outdated interpretations, simplified explanations, or contradictory claims. That creates a high risk of incorrect citations and weakens the trustworthiness of compliance answers.

Because this system is meant to justify answers with evidence, corpus quality matters more than corpus size in the first release.

## Decision

The first release will restrict the RAG corpus to official JR Pass and regional-pass materials only.

Allowed source types:

- official JR pass rule pages
- official regional pass descriptions
- official FAQ pages
- official notices for validity, eligibility, or fare changes

Unofficial travel blogs, community summaries, and forum discussions are excluded from the retrieval corpus.

## Status

Accepted

## Consequences

### Positive

- improves citation trustworthiness
- reduces hallucination caused by conflicting secondary sources
- keeps compliance answers grounded in authoritative material
- makes evaluation easier because retrieved evidence has a clear authority level

### Negative

- reduces corpus breadth in the short term
- may leave some user questions unanswered if official documentation is sparse
- requires more careful source collection and curation

### Follow-up implications

- future expansion to secondary sources would need a separate authority label and retrieval policy
- the ingestion pipeline must validate source provenance before indexing

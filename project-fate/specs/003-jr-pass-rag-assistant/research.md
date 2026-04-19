# Research Notes: JR Pass Official Rules & Compliance RAG

## Decision 1: Use official JR Pass documents as the only first-release corpus

**Decision**: Restrict the first-release knowledge base to official JR Pass and supported regional pass documents, including coverage, validity, qualification, and restrictions.

**Rationale**:
- Maximizes trustworthiness for compliance-oriented answers.
- Reduces hallucination risk from secondary or outdated blog content.
- Aligns with the feature goal of official-rule consultation.

**Alternatives considered**:
- Mix official docs with blogs or travel forums: rejected because authority and revision control are weaker.
- Open-web crawling for broader coverage: rejected because source reliability is too unstable for compliance use.

## Decision 2: Separate rule retrieval from compliance judgment

**Decision**: Build a dedicated `ComplianceAssessment` layer after retrieval instead of letting the generation model infer eligibility directly from retrieved text alone.

**Rationale**:
- Keeps official evidence distinct from system interpretation.
- Improves explainability and testability.
- Makes edge-case handling and rule conflicts easier to reason about.

**Alternatives considered**:
- Pure generation-only reasoning after retrieval: rejected because it weakens traceability and can blur evidence versus inference.

## Decision 3: Track source revision metadata on every ingested chunk

**Decision**: Every pass rule chunk must include source URL, pass product, revision date, and rule category metadata.

**Rationale**:
- Enables conflict detection between revisions.
- Supports answer traceability and debugging.
- Makes future content refresh workflows easier to verify.

**Alternatives considered**:
- Store plain text chunks without revision info: rejected because it undermines compliance trust and version awareness.

## Decision 4: First release is `zh-TW` only

**Decision**: Limit the first release to Traditional Chinese output.

**Rationale**:
- Reduces terminology drift during evaluation.
- Simplifies prompt design, answer evaluation, and consistency checks.
- Matches the primary user context for the current project.

**Alternatives considered**:
- Immediate multilingual output: rejected because it increases ambiguity, terminology alignment cost, and evaluation scope.

## Decision 5: Treat cost comparison as supporting output, not authoritative evidence

**Decision**: Use cost comparison only as a supplementary explanation beside official rule-based consultation.

**Rationale**:
- The system's core role is compliance and rule consultation.
- Cost estimation may be approximate and should not be mistaken for official fare guarantees.

**Alternatives considered**:
- Make cost estimation the primary answer driver: rejected because it would shift the product toward a fare optimizer instead of a rules-based RAG system.

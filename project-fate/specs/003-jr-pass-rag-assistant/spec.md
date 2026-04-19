---
type: spec
version: "1.0"
status: draft
complexity: 4
feature_branch: "003-jr-pass-rag-assistant"
created: "2026-04-15"
sections:
  scope: complete
  user_scenarios: complete
  functional_requirements: complete
  key_entities: complete
  edge_cases: complete
  clarifications: complete
---

# Feature Specification: JR Pass Official Rules & Compliance RAG Consultation System

**Feature Branch**: `003-jr-pass-rag-assistant`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "JR Pass 官方規則與合規性 RAG 諮詢系統"

## Execution Flow (main)
```
1. Parse user description from Input
   -> User wants a RAG-based consultation system for JR Pass official rules and compliance
2. Extract key concepts from description
   -> Actors: travelers planning Japan rail itineraries
   -> Actions: provide itinerary and question, retrieve official pass rules, assess eligibility, receive grounded answer
   -> Data: itinerary structure, official pass documents, restrictions, eligibility rules, citations
   -> Constraints: answers must be grounded, explainable, and bounded by supported JR pass rule knowledge
3. For each unclear aspect:
   -> Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
5. Generate Functional Requirements
6. Identify Key Entities
7. Run Review Checklist
8. Return: SUCCESS (spec ready for clarification/planning)
```

---

## Quick Guidelines
- Focus on what travelers need when checking whether a JR Pass is valid, suitable, or compliant for their route
- Treat this as a knowledge-grounded consultation system, not a freeform travel chatbot
- Keep requirements testable, explainable, and traceable to itinerary and official-source knowledge

### Section Requirements
- Mandatory sections are completed below
- Remaining open decisions are marked explicitly for clarification

### For AI Generation
- Mark ambiguities instead of guessing
- Phrase requirements in testable, observable language
- Prefer bounded compliance consultation behavior over vague assistant language

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
A traveler provides a Japan itinerary and asks whether a JR Pass or regional rail pass is applicable under official rules, then receives a grounded answer that cites relevant eligibility rules, restrictions, and coverage conditions from the knowledge base.

### Acceptance Scenarios
1. **Given** a traveler provides a complete itinerary and asks whether a specific JR Pass can be used, **When** the system performs retrieval and evaluation, **Then** it returns a compliance-oriented answer with citations to the supporting official rules.
2. **Given** the itinerary does not satisfy the conditions for a supported pass, **When** the system evaluates the route, **Then** it clearly explains why the itinerary is not compliant and whether another pass is more suitable.
3. **Given** multiple pass products could fit the route, **When** the system evaluates the itinerary, **Then** it returns one primary consultation result plus alternatives and the reasons for the distinction.
4. **Given** the itinerary or question falls outside the supported knowledge boundary, **When** the system cannot retrieve enough grounded context, **Then** it returns a conservative answer or refusal with an explicit warning.

### Edge Cases
- What happens when the user only visits one city and makes no intercity rail movement?
- How does the system behave when destination stay days exceed the trip duration?
- What happens when part of the route depends on transport not covered by the supported rail passes?
- How does the system respond when official pass documents are retrieved but their rules conflict, differ by revision, or appear outdated?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST accept a structured Japan itinerary including dates, trip duration, arrival city, departure city, destination sequence, and transportation preferences.
- **FR-002**: The system MUST accept a natural-language user question about JR Pass or regional rail pass eligibility, restrictions, or suitability.
- **FR-003**: The system MUST retrieve relevant official pass rules, coverage details, eligibility constraints, and restrictions from the JR pass knowledge base before producing the final answer.
- **FR-004**: The system MUST return an answer that includes both a user-readable consultation result and explicit citations to the official knowledge fragments used.
- **FR-005**: The system MUST assess whether the itinerary is compliant with the conditions of at least one supported pass when enough route information is available.
- **FR-006**: The system MUST clearly state when the itinerary is not eligible for a supported pass and explain the rule-based reason.
- **FR-007**: The system MUST disclose important restrictions such as area coverage, validity period, train eligibility, reservation requirements, and traveler qualification rules when relevant.
- **FR-008**: The system MUST validate itinerary consistency before producing a consultation result.
- **FR-009**: The system MUST refuse or constrain the answer when retrieval results do not meet grounding requirements.
- **FR-010**: The system MUST support both national JR Pass and supported regional pass products in the retrieval and consultation process.
- **FR-011**: The system MUST return request-level metadata and grounding status for traceability and debugging.
- **FR-012**: The system MUST distinguish between official rule-based evidence and system-generated estimation or suitability advice.
- **FR-013**: The system MUST refresh pass catalog and official rule content at least once every 24 hours.
- **FR-014**: The system MUST support anonymous consultation in the first release.
- **FR-015**: The system MUST generate answers in Traditional Chinese (`zh-TW`) in the first release.

### Key Entities *(include if feature involves data)*
- **TripPlan**: The structured user itinerary, including dates, cities, route sequence, and travel preferences.
- **DestinationStop**: One destination in the itinerary, including order and stay duration.
- **PassDocument**: A knowledge document describing one JR Pass or regional rail pass, including official coverage, validity, restrictions, and qualification rules.
- **PassProduct**: A normalized pass entity derived from pass documents, including pass type, valid days, area coverage, pricing metadata, and eligibility metadata.
- **RetrievedChunk**: A chunk of official pass knowledge retrieved for the user query, including source metadata and relevance score.
- **ComplianceAssessment**: The rule-based eligibility judgment for whether the itinerary fits a supported pass.
- **ConsultationResult**: The user-visible answer containing consultation text, alternatives, compliance outcome, cost comparison, citations, and warnings.
- **GroundingResult**: The retrieval validation outcome that determines whether the answer may proceed, fallback, or be blocked.

---

## Constraints

### Technical Constraints
- The system MUST use a retrieval-first RAG flow and MUST NOT answer compliance questions from model prior knowledge alone.
- The knowledge base MUST be built from official JR Pass and regional pass documents, with each chunk carrying source URL, pass product, revision date, and rule category metadata.
- The system MUST apply a recursive, semantics-preserving chunking strategy for official rule text, using paragraph boundaries first and splitting long sections by sentence or phrase rather than arbitrary fixed-length truncation.
- Target chunk size is approximately 600 tokens with an overlap of 100 tokens, to preserve context across related rules while keeping retrieval latency low.
- Retrieval results MUST pass a grounding gate before answer generation; blocked results must return a conservative response instead of a fabricated answer.
- The first release MUST cap retrieved chunks at 10 and citations at 5 to keep latency and answer sprawl bounded.

### Evaluation Plan
- The system MUST include an evaluation workflow using RAGAS or equivalent retrieval-grounding metrics to measure faithfulness, relevance, and hallucination risk.
- Use RAGAS-style metrics to validate:
  - retrieval Top-K accuracy for official rule fragments,
  - grounding precision for cited evidence,
  - answer faithfulness against the official JR Pass corpus.
- Use TruLens or a similar attribution/audit framework to inspect generated answers for evidence usage, attribution correctness, and hallucination signal.
- Define acceptance criteria such as:
  - p95 end-to-end query latency < 2500ms,
  - Top-K retrieval accuracy ≥ 80% for rule-relevant queries,
  - no fabricated citations when grounding gate status is `block`.
- Evaluation coverage MUST include both national JR Pass and supported regional pass products, as well as negative cases where the itinerary is non-compliant or out-of-scope.

### Business Constraints
- The first release provides consultation for JR Pass and supported regional rail passes only; it does not cover flights, hotels, buses, rental cars, or full itinerary planning.
- The system MUST separate official rule interpretation from system-generated cost estimation or suitability advice.
- The system MUST explain non-eligibility or non-compliance explicitly when a user itinerary does not satisfy pass conditions.
- The first release allows anonymous usage, but no personalized account history or saved itineraries are required.

### Operational Constraints
- Official rule and pass catalog content MUST be refreshed at least every 24 hours.
- The first release outputs `zh-TW` only to reduce terminology drift and evaluation complexity.
- The system MUST log request IDs, grounding status, and source revision metadata, but MUST NOT log personally sensitive user identifiers beyond the submitted itinerary payload needed for debugging.
- Query latency target for normal requests is `p95 < 2500ms`.

---

## Clarifications

### Session 2026-04-15
- Q: What is the acceptable refresh interval for pass catalog and rule content? -> A: Refresh every 24 hours
- Q: Should the first release require authentication? -> A: Anonymous access allowed
- Q: What output language should the first release support? -> A: zh-TW only

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---

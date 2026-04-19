---
type: plan
version: "1.0"
status: complete
feature_branch: "003-jr-pass-rag-assistant"
created: "2026-04-15"
phases:
  phase_0_research: complete
  phase_1_design: complete
  phase_2_tasks: complete
constitution_check: pass
---

# Implementation Plan: JR Pass Official Rules & Compliance RAG Consultation System

**Branch**: `003-jr-pass-rag-assistant` | **Date**: 2026-04-15 | **Spec**: [spec.md](/c:/Users/12ok4/project/data-science-2026/project-fate/specs/003-jr-pass-rag-assistant/spec.md)
**Input**: Feature specification from `/specs/003-jr-pass-rag-assistant/spec.md`

## Summary
Build a retrieval-first RAG consultation system for JR Pass official rules and compliance. The system ingests official JR Pass and regional pass rule documents, chunks and embeds them with provenance metadata, retrieves rule evidence for a user itinerary and question, validates grounding, performs eligibility assessment, and returns a Traditional Chinese consultation answer with citations and bounded cost/suitability guidance.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: OpenAI SDK, pytest, behave, vector database client, HTML/document loaders, markdown/text normalization utilities  
**Storage**: Existing vector database abstraction + pass document metadata registry + optional cached itinerary evaluation store  
**Testing**: pytest unit tests, integration tests, retrieval evaluation tests, behave feature scenarios  
**Target Platform**: Linux-compatible Python service / CLI-backed ingestion jobs  
**Project Type**: single  
**Performance Goals**: normal consultation query `p95 < 2500ms`, retrieved chunks <= 10, citations <= 5  
**Constraints**: retrieval-first only, official documents only, `zh-TW` output only in first release, anonymous access, refresh official content every 24 hours  
**Scale/Scope**: first release covers national JR Pass plus a bounded set of supported regional passes and their official rule revisions

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Reference**: See `.agent/memory/constitution.md`

### Principle I: Testable Changes
- [x] Contract tests identified for all API endpoints
- [x] Integration tests identified for all user workflows
- [x] Unit tests identified for retrieval, rule parsing, compliance assessment, and grounding logic
- [x] TDD workflow preserved in task planning approach

### Principle II: Type Safety First
- [x] Input schemas planned for itinerary and query inputs
- [x] Strongly typed domain entities planned for pass rules, products, and assessments
- [x] Retrieval metadata and compliance outputs normalized before answer generation

### Principle III: Security by Default
- [x] Input validation planned for all user inputs
- [x] No sensitive user identifiers required beyond itinerary payload
- [x] Logging scope bounded to request IDs, grounding state, and source metadata

### Principle IV: Code Quality & Maintainability
- [x] Documentation artifacts planned for research, data model, contracts, and quickstart
- [x] Test coverage targets defined for unit and integration layers
- [x] Feature branch and file layout remain incremental and localized

### Principle V: Small, Reversible Steps
- [x] Query path reuses existing ingestion/retrieval foundation where possible
- [x] Compliance assessment added as a bounded domain layer instead of broad trip-planning logic
- [x] Source coverage limited to supported official pass documents in first release

### Principle VI: Human Authority
- [x] Official-source curation remains explicit
- [x] System provides consultation, not legally binding or commercial guarantee
- [x] Rule conflicts and insufficient evidence produce conservative output

## Project Structure

### Documentation (this feature)
```text
specs/003-jr-pass-rag-assistant/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- jr-pass-compliance.openapi.yaml
`-- tasks.md
```

### Source Code (repository root)
```text
src/
|-- models/
|   |-- knowledge.py
|   `-- pass_rules.py                # new
|-- ingestion/
|   |-- ingestor.py
|   |-- chunker.py
|   |-- embedder.py
|   `-- pass_rule_ingestor.py        # new
|-- retrieval/
|   |-- retrieval_gate.py
|   `-- pass_rule_retriever.py       # new
|-- query/
|   |-- query_pipeline.py
|   `-- compliance_consultation.py   # new
|-- governance/
|   `-- source_policy.py             # new
|-- config/
|   `-- pass_catalog_config.py       # new
`-- rag/
    `-- core.py

tests/
|-- contract/
|   `-- test_jr_pass_compliance_contract.py   # new
|-- integration/
|   `-- test_jr_pass_consultation_flow.py     # new
`-- unit/
    |-- test_pass_rule_ingestor.py            # new
    |-- test_pass_rule_retriever.py           # new
    `-- test_compliance_assessment.py         # new
```

**Structure Decision**: Single Python project. Extend the existing ingestion/retrieval/query architecture with a narrowly scoped pass-rule ingestion and compliance assessment layer instead of introducing a separate microservice.

## Phase 0: Outline & Research

Research output is captured in [research.md](/c:/Users/12ok4/project/data-science-2026/project-fate/specs/003-jr-pass-rag-assistant/research.md).

Resolved research topics:
- use official JR Pass documents only as first-release corpus
- split rule retrieval from cost/suitability estimation
- model revision-aware pass documents with source provenance
- keep multilingual expansion out of first release

**Output**: `research.md` complete

## Phase 1: Design & Contracts

Design output is captured in:
- [data-model.md](/c:/Users/12ok4/project/data-science-2026/project-fate/specs/003-jr-pass-rag-assistant/data-model.md)
- [quickstart.md](/c:/Users/12ok4/project/data-science-2026/project-fate/specs/003-jr-pass-rag-assistant/quickstart.md)
- [jr-pass-compliance.openapi.yaml](/c:/Users/12ok4/project/data-science-2026/project-fate/specs/003-jr-pass-rag-assistant/contracts/jr-pass-compliance.openapi.yaml)

Phase 1 design decisions:
1. Add a pass-rule ingestion layer for official JR pass documents with revision metadata.
2. Separate `PassDocument` retrieval from `ComplianceAssessment` logic so grounded evidence and derived judgment remain distinguishable.
3. Keep `grounding gate` as a mandatory checkpoint before answer generation.
4. Limit first release to `zh-TW` output and anonymous consultation to reduce scope and ambiguity.
5. Use bounded cost comparison only as a supporting output, not as the primary authoritative source.

**Output**: data model, quickstart, and contracts completed

## Phase 2: Task Planning Approach

**Task Generation Strategy**:
- Generate contract tests for the consultation endpoint first.
- Generate unit tests for rule ingestion, retrieval metadata filtering, compliance assessment, and grounding behavior.
- Generate integration tests for the full ingest -> retrieve -> assess -> answer workflow.
- Implement domain models and config before retriever and consultation orchestration.
- Implement answer-generation wiring only after retrieval and compliance outputs are testable.

**Ordering Strategy**:
- TDD order: contracts -> unit tests -> integration tests -> implementation
- Dependency order: models/config -> ingestion -> retriever -> compliance logic -> API/query wiring
- Parallelizable tasks: unit tests for ingestion, retrieval, and compliance logic can proceed independently

**Estimated Output**: 18-24 ordered tasks in `tasks.md`

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Add explicit compliance assessment layer | The system must distinguish official rule retrieval from eligibility judgment | Pure freeform generation would blur evidence and judgment boundaries |
| Add revision-aware rule metadata | Official documents may conflict across revisions | Flat documents without revision tracking would weaken trust and explainability |

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution: `.agent/memory/constitution.md`*

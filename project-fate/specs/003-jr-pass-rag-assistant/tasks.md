---
type: tasks
version: "1.0"
status: pending
feature_branch: "003-jr-pass-rag-assistant"
created: "2026-04-15"
total_tasks: 20
completed_tasks: 0
phases:
  setup: pending
  tests: pending
  core: pending
  integration: pending
  polish: pending
---

# Tasks: JR Pass Official Rules & Compliance RAG Consultation System

**Input**: Design documents from `/specs/003-jr-pass-rag-assistant/`
**Prerequisites**: `plan.md`, `research.md`, `data-model.md`, `contracts/jr-pass-compliance.openapi.yaml`

## Phase 3.1: Setup
- [ ] T001 Create `src/models/pass_rules.py` with typed entities for `PassDocument`, `PassProduct`, `RetrievedChunk`, and `ComplianceAssessment`
- [ ] T002 Create `src/config/pass_catalog_config.py` for refresh interval, supported pass set, and query-time limits
- [ ] T003 Create `src/governance/source_policy.py` to enforce official-source-only ingestion rules

## Phase 3.2: Tests First (TDD)
- [ ] T004 [P] Create contract test for `POST /api/jr-pass-compliance-rag/query` in `tests/contract/test_jr_pass_compliance_contract.py`
- [ ] T005 [P] Create unit tests for rule ingestion metadata validation in `tests/unit/test_pass_rule_ingestor.py`
- [ ] T006 [P] Create unit tests for retrieval filtering and revision handling in `tests/unit/test_pass_rule_retriever.py`
- [ ] T007 [P] Create unit tests for compliance assessment outcomes in `tests/unit/test_compliance_assessment.py`
- [ ] T008 [P] Create integration test for end-to-end consultation flow in `tests/integration/test_jr_pass_consultation_flow.py`

## Phase 3.3: Core Implementation
- [ ] T009 Implement official pass rule ingestion bridge in `src/ingestion/pass_rule_ingestor.py`
- [ ] T010 Implement pass rule retriever with metadata-aware search in `src/retrieval/pass_rule_retriever.py`
- [ ] T011 Implement compliance assessment service in `src/query/compliance_consultation.py`
- [ ] T012 Extend `src/models/knowledge.py` or supporting model layer to preserve source URL, revision date, and rule category metadata
- [ ] T013 Add request validation schema and itinerary normalization for consultation queries in `src/query/compliance_consultation.py`
- [ ] T014 Wire retrieval gate + compliance assessment + generation flow into `src/query/query_pipeline.py`
- [ ] T015 Update `src/rag/core.py` prompt contract so answers distinguish official rules from estimation

## Phase 3.4: Integration
- [ ] T016 Connect official rule ingestion to existing chunking and embedding flow in `src/ingestion/chunker.py`, `src/ingestion/embedder.py`, and `src/ingestion/pass_rule_ingestor.py`
- [ ] T017 Add source-policy enforcement and refresh scheduling hooks in `src/governance/source_policy.py` and `src/config/pass_catalog_config.py`
- [ ] T018 Implement the consultation API handler for `POST /api/jr-pass-compliance-rag/query` in the appropriate application entrypoint or adapter layer

## Phase 3.5: Polish
- [ ] T019 Add retrieval-quality evaluation coverage for JR pass rule relevance in `tests/evaluation/test_retrieval_quality.py`
- [ ] T020 Update repository-facing documentation with feature usage notes in `docs/AI/20260408_bazi_rag_spec.md` and related docs if needed

## Dependencies
- T004-T008 must be written before T009-T018
- T001 blocks T009-T014
- T002 and T003 block T017
- T009 and T010 block T011 and T014
- T011 and T014 block T018
- T018 blocks T019

## Parallel Example
```text
Run in parallel:
- T004 tests/contract/test_jr_pass_compliance_contract.py
- T005 tests/unit/test_pass_rule_ingestor.py
- T006 tests/unit/test_pass_rule_retriever.py
- T007 tests/unit/test_compliance_assessment.py
- T008 tests/integration/test_jr_pass_consultation_flow.py
```

## Validation Checklist
- [ ] Contract test exists for the consultation endpoint
- [ ] All core entities have implementation tasks
- [ ] Tests are scheduled before implementation
- [ ] Parallel tasks do not edit the same file
- [ ] Each task specifies exact file paths


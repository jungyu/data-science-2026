# Quickstart: JR Pass Compliance RAG Flow

## Goal

Validate that the system can ingest official JR pass rules, retrieve relevant rule fragments, assess eligibility, and return a grounded consultation answer.

## Preconditions

- Feature branch: `003-jr-pass-rag-assistant`
- Official JR pass documents are available for ingestion
- Vector DB and embedding configuration are available
- The consultation endpoint is wired to retrieval and grounding components

## Scenario 1: Ingest official pass rules

1. Load one official JR Pass rule document and one regional pass rule document.
2. Chunk and embed each document with source URL, pass product, revision date, and rule category metadata.
3. Verify the documents are queryable in the vector store.

## Scenario 2: Ask a compliance question

1. Submit a structured itinerary plus a question such as:
   `東京進大阪出，7 天跑東京、京都、金澤，是否符合全國版 JR Pass 使用條件？`
2. Verify the system retrieves relevant official rule chunks.
3. Verify the grounding gate allows answer generation when evidence is sufficient.

## Scenario 3: Receive a grounded consultation answer

1. Verify the answer includes:
   - consultation result
   - rule-based explanation
   - citations
   - compliance outcome
2. Verify the answer distinguishes official rules from system estimation.

## Scenario 4: Handle non-eligibility

1. Submit an itinerary that does not satisfy any supported pass conditions.
2. Verify the system explicitly states non-eligibility.
3. Verify the answer cites the rules behind that decision.

## Scenario 5: Handle insufficient grounding

1. Submit a question or route outside supported document coverage.
2. Verify the grounding gate blocks or constrains the answer.
3. Verify the system returns warnings instead of fabricated guidance.

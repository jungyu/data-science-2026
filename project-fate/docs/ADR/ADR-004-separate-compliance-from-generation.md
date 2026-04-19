# ADR-004: Separate Compliance Assessment from Generative Answering

## Context

JR Pass consultation requires more than retrieving text. The system must decide whether an itinerary appears eligible under official rules, whether restrictions apply, and whether the answer should be conservative when evidence is incomplete.

If a single generative step directly consumes itinerary data and retrieved chunks, it may blur together three different tasks:

- retrieving official rules
- assessing compliance against those rules
- generating a user-facing explanation

That makes the system harder to test, harder to audit, and more likely to mix evidence with unsupported inference.

## Decision

The system will use three logical layers:

1. `Rule Retrieval Layer`
   Retrieves official JR rule evidence.
2. `Compliance Assessment Layer`
   Interprets the itinerary against retrieved rules and produces a structured judgment.
3. `Answer Generation Layer`
   Produces the final explanation using retrieved evidence and the compliance outcome.

The answer generation layer must not invent compliance status that is not supported by the assessment layer.

## Status

Accepted

## Consequences

### Positive

- improves testability of rule reasoning
- separates evidence retrieval from judgment logic
- makes it easier to explain which part of the system produced each conclusion
- reduces the chance of unsupported compliance claims

### Negative

- adds architectural complexity compared with a simple vector-RAG pipeline
- requires explicit interfaces between retrieval, assessment, and generation

### Follow-up implications

- evaluation can score retrieval quality and compliance quality separately
- future rule engines or deterministic validators can replace or augment the assessment layer without rewriting generation

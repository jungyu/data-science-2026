# Data Model: JR Pass Official Rules & Compliance Consultation

## Entity: TripPlan

Represents the structured itinerary provided by the user.

| Field | Type | Notes |
|------|------|-------|
| trip_id | string | Request-scoped identifier |
| start_date | date | Trip start date |
| duration_days | integer | Total trip days |
| arrival_city | string | First entry city |
| departure_city | string | Exit city |
| transport_preferences | list[string] | Preferred rail modes |
| locale | string | Output language, first release `zh-TW` |

## Entity: DestinationStop

Represents one stop in the itinerary sequence.

| Field | Type | Notes |
|------|------|-------|
| stop_id | string | Unique stop identifier |
| trip_id | string | Parent trip |
| sequence | integer | Visit order |
| city | string | City or region |
| stay_days | integer | Stay duration |

## Entity: PassDocument

Represents one official pass source document prior to chunk retrieval.

| Field | Type | Notes |
|------|------|-------|
| doc_id | string | Unique document identifier |
| pass_name | string | Official pass name |
| pass_type | enum | `national`, `regional` |
| source_url | string | Official source URL |
| revision_date | datetime | Source revision timestamp |
| language | string | Source language |
| rule_category | string | E.g. coverage, eligibility, restrictions, reservations |
| status | enum | `active`, `superseded`, `draft` |

## Entity: PassProduct

Represents a normalized pass object derived from one or more official documents.

| Field | Type | Notes |
|------|------|-------|
| product_id | string | Unique product identifier |
| pass_name | string | Canonical pass name |
| pass_type | enum | `national`, `regional` |
| coverage_area | string | Area description |
| valid_days | integer | Ticket validity |
| qualification_rules | list[string] | Traveler eligibility rules |
| train_restrictions | list[string] | Covered and excluded train types |
| price_version | string | Price version marker |

## Entity: RetrievedChunk

Represents one retrieved rule fragment used for answer grounding.

| Field | Type | Notes |
|------|------|-------|
| chunk_id | string | Unique chunk identifier |
| doc_id | string | Parent pass document |
| pass_name | string | Canonical pass name |
| rule_category | string | Restriction / coverage / validity / qualification |
| excerpt | string | Retrieved text |
| relevance_score | float | Retrieval score |
| revision_date | datetime | Revision inherited from source |

## Entity: ComplianceAssessment

Represents the system's rule-based judgment after retrieval.

| Field | Type | Notes |
|------|------|-------|
| assessment_id | string | Unique assessment identifier |
| eligible | boolean | Whether the itinerary fits pass conditions |
| rule_summary | string | Short explanation |
| violated_rules | list[string] | Reasons for non-eligibility |
| candidate_passes | list[string] | Plausible products |

## Entity: ConsultationResult

Represents the final user-visible output.

| Field | Type | Notes |
|------|------|-------|
| request_id | string | Request ID |
| answer | string | Final consultation text |
| summary | string | Short summary |
| citations | list[RetrievedChunk] | Supporting evidence |
| warnings | list[string] | Grounding or scope warnings |
| compliance_assessment | ComplianceAssessment | Linked judgment |

## Relationships

- One `TripPlan` has many `DestinationStop`
- One `PassDocument` yields many `RetrievedChunk`
- Many `PassDocument` records can contribute to one `PassProduct`
- One `ConsultationResult` references one `ComplianceAssessment`

## Validation Rules

- `duration_days` must be >= total stay days across all stops
- `DestinationStop.sequence` must be unique within a `TripPlan`
- `RetrievedChunk` must include `source_url` through its parent document metadata
- `ComplianceAssessment.eligible = false` must include at least one `violated_rules` entry
- `ConsultationResult.citations` must be empty only when grounding gate status is `block`

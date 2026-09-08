# Failure modes

| Failure | Behaviour |
| --- | --- |
| LMS unavailable | Degraded connector, last snapshot, uncertainty flagged |
| Email permission revoked | No new mail, fail closed |
| Grok timeout / offline | Fake adapter or explicit error; never silent success |
| Conflicting deadlines | `conflicted` + human queue |
| Ambiguous date | `needs_review`, no invented timestamp |
| Calendar write failure | Audit `failed`, approval not marked applied |
| Duplicate obligation | Merge, keep both claims |
| Invalid model JSON | Fall back to deterministic extractor, log warning |
| Prompt injection | Ignored, audit event |
| Infeasible plan | `feasible=false`, unsatisfied hard constraints listed |
| Approval expired | HTTP 409 `approval_expired` |
| Duplicate write | `status=idempotent` |
| Internet down during demo | Frozen fixtures + FakeGrokAdapter |

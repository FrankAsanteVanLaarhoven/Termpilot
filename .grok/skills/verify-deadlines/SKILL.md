---
name: verify-deadlines
description: Deduplicate extracted obligations, detect conflicting deadlines, and assign verification states. Use when verifying claims or running /verify-deadlines.
---

# verify-deadlines

## Inputs

- Candidate obligations
- Source observations

## Output (JSON only)

Deduplicated obligations, conflicting claims, verification state, reason code, evidence references.

## Verification states

`verified` | `probable` | `needs_review` | `conflicted` | `rejected`

## Rules

1. A newer source is not automatically authoritative.
2. Material conflicts require user review. Never silently resolve them.
3. Never hide discarded evidence.
4. Reject obligations without minimum evidence.
5. Ambiguous dates stay `needs_review`.

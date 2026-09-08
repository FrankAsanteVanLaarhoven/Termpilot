# Privacy and safety

- Minimum fields only. Display name is a synthetic label.
- Consent is explicit, purpose-scoped and revocable (`consent_grants`).
- Operational records use pseudonymous IDs (`usr_demo_a7f3`).
- Logs redact tokens, passwords and raw email bodies.
- Raw source JSON is retained at most 72 hours in the demo configuration.
- HTTPS is expected in production; local demo is HTTP on loopback.
- Encryption at rest is the host disk / database offering. The MVP does not add a second crypto layer.
- Export: `GET /export`. Delete: `DELETE /export` (demo reset).
- No inference of disability, health or academic ability.
- No institution-level analytics in this MVP.

## Threats handled

| Threat | Control |
| --- | --- |
| Prompt injection | Strip instruction-like sentences; never execute them |
| Cross-user access | `X-User-Id` scoped queries; demo single-user |
| Missing authorisation | Consent fail-closed |
| Replayed approval | Idempotency key + applied state |
| Duplicate calendar write | UID + approval_id lookup |
| Path traversal / oversized upload | Connector rejects `..`, `/` and files > 256 KB |
| Homework completion | Guardian blocks |

# E25: Authentication and Request Isolation

Generated: 2026-09-26T23:31:48.992100+00:00

## Config

- **acs**: fake, real WebSocket server
- **real_token_scheme**: single shared secret, no per-robot identity

## Metrics

- **testable_cases**: 3
- **correctly_handled**: 3
- **not_representable_cases**: 4
- **valid_token_is_replayable**: True

## Notes

3 of 6 PDF-requested scenarios are not representable against the real auth scheme: it is a single shared secret with no per-robot identity, expiry, or request nonce at all. Of what IS testable: valid/invalid/empty tokens are all handled correctly (accept/reject/reject), but a valid token can be replayed indefinitely - there is no mechanism preventing reuse. This is exactly the limitation the paper's Discussion already names as 'adequate for one robot and one ACS instance in development but not for a multi-robot or multi-tenant deployment' - this experiment is the empirical confirmation of that claim, not a new finding.

Full per-trial records: `E25_authentication_and_request_isolation.json`

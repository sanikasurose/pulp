API Design Checklist
Use this checklist when reviewing new API endpoints before shipping to production.
Authentication & Authorisation
1. All endpoints require authentication unless explicitly documented as public.
2. Authorisation checks are enforced at the service layer, not just the gateway.
3. OAuth 2.0 scopes are defined and documented for each endpoint.
4. Token expiry and refresh flows are tested end-to-end.
Input Validation
5. All request parameters are validated against a schema before processing.
6. String inputs are length-bounded to prevent abuse.
7. Numeric inputs have explicit min/max constraints.
8. File uploads are type-checked and size-limited.
Error Handling
9. Errors return RFC 7807 Problem Details responses.
10. Validation errors enumerate all failing fields, not just the first.
11. Internal errors never leak stack traces to API consumers.
12. Rate limiting returns 429 with Retry-After header.
Documentation
13. OpenAPI spec is generated from code annotations, not written by hand.
14. Each endpoint has at least one example request and response.
15. Breaking changes are noted with a deprecation timeline.

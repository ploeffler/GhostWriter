# GhostWriter API

Cloudflare Workers foundation for the GhostWriter GPT Action API.

## Current status

The Worker is not deployed and is not production-ready.

Implemented:
- \`GET /v1/health\` (public)
- \`GET /v1/account\` (Auth0 JWT validation; requires \`read:account\`)
- RS256 signature validation against Auth0 JWKS
- issuer, audience, expiry and subject validation
- basic response security headers and no-store
- TypeScript type-check and unit-test setup

Not implemented:
- Auth0 tenant/client configuration (manual dashboard setup required)
- GitHub App authorization and token storage
- repository listing and permission checks
- project read/write operations
- idempotency storage and expected-head-SHA checks
- production OpenAPI document

## Requirements

- Node.js 20 or newer
- npm

## Local development

\`\`\`sh
npm install
cp .dev.vars.example .dev.vars
# Replace the example Auth0 issuer and audience with your Auth0 values.
npm run typecheck
npm test
npm run dev
\`\`\`

Then check \`http://localhost:8787/v1/health\`.

## Auth0 environment values

- \`AUTH0_ISSUER\`: exact HTTPS issuer URL from your Auth0 tenant, including trailing slash.
- \`AUTH0_AUDIENCE\`: the API Identifier configured in Auth0.

These values are not secrets. The GPT Action's Auth0 client secret belongs in the GPT Action authentication settings, not here. Never commit \`.dev.vars\`.

## Deployment

Do not deploy publicly until the Auth0 tenant, GPT Action handshake, JWT/scope integration tests, GitHub authorization, production OpenAPI document, privacy policy and production domain are ready.

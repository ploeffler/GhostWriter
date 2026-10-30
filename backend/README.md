# GhostWriter API

Cloudflare Workers foundation for the future GhostWriter GPT Action API.

## Current status

Initial runtime scaffold only; not deployed and not production-ready.

Implemented:
- `GET /v1/health`
- JSON error response for unknown routes
- no-store and basic response security headers
- TypeScript type-check and unit-test setup

Not implemented:
- GPT Action authentication
- GitHub user authorization / GitHub App integration
- repository listing and permission checks
- project read/write operations
- idempotency storage and expected-head-SHA checks
- production OpenAPI document

No credentials, tokens, repository content, or book data belong here.

## Requirements

- Node.js 20 or newer
- npm

## Local development

```sh
npm install
npm run typecheck
npm test
npm run dev
```

Then check `http://localhost:8787/v1/health`.

## Deployment

Production deployment is intentionally not enabled yet. Before deployment:
1. implement and test authentication;
2. implement GitHub authorization and repository-level access checks;
3. add required Cloudflare bindings and secrets;
4. generate OpenAPI from the implemented routes;
5. run security and integration tests;
6. configure a production domain and GPT Action OAuth settings.

Use Wrangler secrets for credentials. Never put secrets in `wrangler.jsonc`, source files, prompts, or Git.

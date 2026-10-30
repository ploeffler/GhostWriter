import { authenticateRequest, hasScope, type AuthConfig } from "./auth";

export interface Env extends AuthConfig {
  APP_ENV?: string;
}

const headers = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/v1/health") {
      if (request.method !== "GET") {
        return new Response(null, { status: 405, headers: { allow: "GET", ...headers } });
      }
      return json({ service: "ghostwriter-api", api_version: "v1", status: "ok" });
    }

    if (url.pathname === "/v1/account") {
      if (request.method !== "GET") {
        return new Response(null, { status: 405, headers: { allow: "GET", ...headers } });
      }
      const user = await authenticateRequest(request, env);
      if (!user) {
        return json({ error: { code: "UNAUTHENTICATED", message: "A valid GhostWriter sign-in is required." } }, 401);
      }
      if (!hasScope(user, "read:account")) {
        return json({ error: { code: "INSUFFICIENT_SCOPE", message: "The access token lacks read:account." } }, 403);
      }
      return json({ user: { id: user.subject }, authorization: { scopes: user.scopes } });
    }

    return json({ error: { code: "NOT_FOUND", message: "The requested endpoint is not implemented." } }, 404);
  }
};

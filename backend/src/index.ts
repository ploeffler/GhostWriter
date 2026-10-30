export interface Env {
  APP_ENV?: string;
}

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders });
}

export default {
  async fetch(request: Request, _env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/v1/health") {
      if (request.method !== "GET") {
        return new Response(null, { status: 405, headers: { allow: "GET", ...jsonHeaders } });
      }
      return json({ service: "ghostwriter-api", api_version: "v1", status: "ok" });
    }

    return json({ error: { code: "NOT_FOUND", message: "The requested endpoint is not implemented." } }, 404);
  }
};

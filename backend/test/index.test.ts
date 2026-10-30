import { describe, expect, it } from "vitest";
import worker from "../src/index";

const env = {
  APP_ENV: "test",
  AUTH0_ISSUER: "https://ghostwriter-test.eu.auth0.com/",
  AUTH0_AUDIENCE: "https://api.ghostwriter.example"
};

describe("GhostWriter API foundation", () => {
  it("returns a public health response", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/health"), env);
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(await response.json()).toEqual({
      service: "ghostwriter-api",
      api_version: "v1",
      status: "ok"
    });
  });

  it("rejects unsupported health methods", async () => {
    const response = await worker.fetch(
      new Request("https://api.example.test/v1/health", { method: "POST" }),
      env
    );
    expect(response.status).toBe(405);
    expect(response.headers.get("allow")).toBe("GET");
  });

  it("requires a bearer token for account access", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/account"), env);
    expect(response.status).toBe(401);
    expect(await response.json()).toMatchObject({
      error: { code: "UNAUTHENTICATED" }
    });
  });

  it("does not expose unimplemented operations", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/repositories"), env);
    expect(response.status).toBe(404);
    expect(await response.json()).toMatchObject({
      error: { code: "NOT_FOUND" }
    });
  });
});

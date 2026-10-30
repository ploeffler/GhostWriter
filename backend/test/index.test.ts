import { describe, expect, it } from "vitest";
import worker from "../src/index";

describe("GhostWriter API foundation", () => {
  it("returns a minimal health response", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/health"), { APP_ENV: "test" });
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(await response.json()).toEqual({ service: "ghostwriter-api", api_version: "v1", status: "ok" });
  });

  it("rejects unsupported health methods", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/health", { method: "POST" }), { APP_ENV: "test" });
    expect(response.status).toBe(405);
    expect(response.headers.get("allow")).toBe("GET");
  });

  it("does not expose unimplemented API operations", async () => {
    const response = await worker.fetch(new Request("https://api.example.test/v1/repositories"), { APP_ENV: "test" });
    expect(response.status).toBe(404);
    expect(await response.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
  });
});

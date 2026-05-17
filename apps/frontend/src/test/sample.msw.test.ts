import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "./msw/server";

describe("MSW sentinel", () => {
  it("intercepts a fetch", async () => {
    server.use(
      http.get("https://api.example.test/ping", () =>
        HttpResponse.json({ ok: true }),
      ),
    );
    const res = await fetch("https://api.example.test/ping");
    const body = await res.json();
    expect(body).toEqual({ ok: true });
  });
});

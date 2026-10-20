import { afterEach, describe, expect, it, vi } from "vitest";
import { getDashboard, login, logout, UnauthorizedError } from "./api";
import { envelope } from "./test/fixtures";

afterEach(() => vi.unstubAllGlobals());

describe("dashboard API client", () => {
  it("submits the password using a credentialed request", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    await login("household secret");
    expect(fetch).toHaveBeenCalledWith("/api/v1/session", expect.objectContaining({
      method: "POST",
      credentials: "include",
      body: JSON.stringify({ password: "household secret" }),
    }));
  });

  it("parses the versioned dashboard response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(envelope)));
    await expect(getDashboard()).resolves.toEqual(envelope);
  });

  it("turns unauthorized responses into session expiration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    await expect(getDashboard()).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it("logs out without exposing any session token", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    await logout();
    expect(fetch).toHaveBeenCalledWith("/api/v1/session", expect.objectContaining({ method: "DELETE", credentials: "include" }));
  });
});

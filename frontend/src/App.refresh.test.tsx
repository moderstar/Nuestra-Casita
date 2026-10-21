import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { DASHBOARD_POLL_INTERVAL_MS, DEVICE_POLL_INTERVAL_MS } from "./App";
import type { ApiEnvelope, Device } from "./types";
import { envelope, snapshot } from "./test/fixtures";

function devices(value = "73.1"): ApiEnvelope<Device[]> {
  return {
    version: "1",
    state: "available",
    data: [{ ...snapshot.devices[0], value }],
    errors: [],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((complete) => { resolve = complete; });
  return { promise, resolve };
}

async function flush() {
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("background refresh", () => {
  it("polls devices every 10 seconds and the full dashboard every 30 seconds", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn((path: string) => Promise.resolve(Response.json(path === "/api/v1/devices" ? devices() : envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();

    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    await flush();
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/devices")).toHaveLength(1);

    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    await flush();
    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    await flush();
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/dashboard")).toHaveLength(2);
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/devices")).toHaveLength(3);
  });

  it("does not poll while hidden and refreshes both sources when visible", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn((path: string) => Promise.resolve(Response.json(path === "/api/v1/devices" ? devices() : envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    await act(async () => { vi.advanceTimersByTime(DASHBOARD_POLL_INTERVAL_MS); });
    expect(fetch).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    fireEvent(document, new Event("visibilitychange"));
    await flush();
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/dashboard")).toHaveLength(2);
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/devices")).toHaveLength(1);
  });

  it("prevents overlapping device requests", async () => {
    vi.useFakeTimers();
    const pending = deferred<Response>();
    const fetch = vi.fn((path: string) => path === "/api/v1/devices" ? pending.promise : Promise.resolve(Response.json(envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS * 2); });
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/devices")).toHaveLength(1);
    pending.resolve(Response.json(devices()));
    await flush();
  });

  it("prevents a manual refresh from overlapping an active dashboard poll", async () => {
    vi.useFakeTimers();
    const pending = deferred<Response>();
    let dashboardReads = 0;
    const fetch = vi.fn((path: string) => {
      if (path === "/api/v1/devices") return Promise.resolve(Response.json(devices()));
      dashboardReads += 1;
      return dashboardReads === 1 ? Promise.resolve(Response.json(envelope)) : pending.promise;
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    await act(async () => { vi.advanceTimersByTime(DASHBOARD_POLL_INTERVAL_MS); });
    fireEvent.click(screen.getByRole("button", { name: "Refresh dashboard" }));
    expect(fetch.mock.calls.filter(([path]) => path === "/api/v1/dashboard")).toHaveLength(2);
    pending.resolve(Response.json(envelope));
    await flush();
  });

  it("does not let an older device response overwrite a newer full snapshot", async () => {
    vi.useFakeTimers();
    window.history.replaceState({}, "", "/home-status");
    const pending = deferred<Response>();
    const newer = { ...envelope, data: { ...snapshot, devices: [{ ...snapshot.devices[0], value: "80.0" }] } };
    let dashboardReads = 0;
    const fetch = vi.fn((path: string) => {
      if (path === "/api/v1/devices") return pending.promise;
      dashboardReads += 1;
      return Promise.resolve(Response.json(dashboardReads === 1 ? envelope : newer));
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    fireEvent.click(screen.getByRole("button", { name: "Refresh dashboard" }));
    await flush();
    expect(screen.getByText("80.0 °F")).toBeInTheDocument();
    pending.resolve(Response.json(devices("60.0")));
    await flush();
    expect(screen.getByText("80.0 °F")).toBeInTheDocument();
    expect(screen.queryByText("60.0 °F")).not.toBeInTheDocument();
  });

  it("preserves device data through a temporary polling failure", async () => {
    vi.useFakeTimers();
    window.history.replaceState({}, "", "/home-status");
    const fetch = vi.fn((path: string) => path === "/api/v1/devices"
      ? Promise.reject(new TypeError("offline"))
      : Promise.resolve(Response.json(envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    expect(screen.getByText("72.4 °F")).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    await flush();
    expect(screen.getByText("72.4 °F")).toBeInTheDocument();
    expect(screen.getByText("Some information may be out of date.")).toBeInTheDocument();
  });

  it("returns to login when a polling request reports session expiration", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn((path: string) => path === "/api/v1/devices"
      ? Promise.resolve(new Response(null, { status: 401 }))
      : Promise.resolve(Response.json(envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    await act(async () => { vi.advanceTimersByTime(DEVICE_POLL_INTERVAL_MS); });
    await flush();
    expect(screen.getByRole("heading", { name: "Welcome home" })).toBeInTheDocument();
  });

  it("keeps an unfinished chore form mounted during background updates", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn((path: string) => {
      if (path === "/api/v1/chore-users") return Promise.resolve(Response.json({ version: "1", state: "available", data: [], errors: [] }));
      if (path === "/api/v1/devices") return Promise.resolve(Response.json(devices()));
      return Promise.resolve(Response.json(envelope));
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    fireEvent.click(screen.getByRole("button", { name: /Chores/ }));
    fireEvent.click(screen.getByRole("button", { name: /Add chore/ }));
    await flush();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Water seedlings" } });
    await act(async () => { vi.advanceTimersByTime(DASHBOARD_POLL_INTERVAL_MS); });
    await flush();
    expect(screen.getByLabelText("Name")).toHaveValue("Water seedlings");
    expect(screen.getByRole("heading", { name: "Create chore" })).toBeInTheDocument();
  });

  it("keeps an unfinished shopping form mounted during background updates", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn((path: string) => Promise.resolve(Response.json(path === "/api/v1/devices" ? devices() : envelope)));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await flush();
    fireEvent.click(screen.getByRole("button", { name: /Shopping/ }));
    fireEvent.click(screen.getByRole("button", { name: /Add item/ }));
    fireEvent.click(screen.getByRole("button", { name: "Free-text item" }));
    fireEvent.change(screen.getByLabelText("Item description"), { target: { value: "Fresh basil" } });
    await act(async () => { vi.advanceTimersByTime(DASHBOARD_POLL_INTERVAL_MS); });
    await flush();
    expect(screen.getByLabelText("Item description")).toHaveValue("Fresh basil");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

describe("URL navigation", () => {
  it("opens a supported direct URL and preserves it", async () => {
    window.history.replaceState({}, "", "/recipes");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(envelope)));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Recipes", level: 1 })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/recipes");
  });

  it("updates the URL without reloading and responds to Back/Forward history events", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(envelope)));
    render(<App />);
    await screen.findAllByText("Our Home");
    fireEvent.click(screen.getByRole("button", { name: /Shopping/ }));
    expect(window.location.pathname).toBe("/shopping");
    expect(screen.getByRole("heading", { name: "Shopping" })).toBeInTheDocument();

    window.history.pushState({}, "", "/inventory");
    fireEvent(window, new PopStateEvent("popstate"));
    expect(screen.getByRole("heading", { name: "Inventory" })).toBeInTheDocument();
    window.history.pushState({}, "", "/shopping");
    fireEvent(window, new PopStateEvent("popstate"));
    expect(screen.getByRole("heading", { name: "Shopping" })).toBeInTheDocument();
  });

  it("canonicalizes an unknown route to Overview", async () => {
    window.history.replaceState({}, "", "/not-a-page");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(envelope)));
    render(<App />);
    await screen.findAllByText("Our Home");
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(screen.getByRole("button", { name: /^Home$/ })).toHaveAttribute("aria-current", "page");
  });
});

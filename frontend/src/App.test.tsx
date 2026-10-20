import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { envelope, snapshot } from "./test/fixtures";

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("kitchen dashboard", () => {
  it("shows login after an unauthenticated session probe and authenticates", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(Response.json(envelope));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Welcome home" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Household password"), "a secure password");
    await userEvent.click(screen.getByRole("button", { name: "Open dashboard" }));
    expect(await screen.findByText("Our Home")).toBeInTheDocument();
    expect(screen.getAllByText("Milk")[0]).toBeInTheDocument();
  });

  it("renders useful empty states without fabricated records", async () => {
    const empty = { ...envelope, state: "empty" as const, data: { ...snapshot, shopping_lists: [], inventory: null } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(empty)));
    render(<App />);
    expect(await screen.findByText("Nothing to pick up")).toBeInTheDocument();
    expect(screen.getByText("No inventory to show")).toBeInTheDocument();
  });

  it("keeps data visible and marks a degraded response", async () => {
    const degraded = { ...envelope, state: "degraded" as const, data: { ...snapshot, stale_sections: ["shopping"] }, errors: [{ code: "integration_unavailable", source: "grocy", capability: "shopping", message: "Integration data could not be loaded." }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(degraded)));
    render(<App />);
    expect(await screen.findByText("Some information may be out of date.")).toBeInTheDocument();
    expect(screen.getByText("Milk")).toBeInTheDocument();
  });

  it("provides touch navigation for every required page", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(envelope)));
    render(<App />);
    await screen.findAllByText("Our Home");
    const shopping = screen.getByRole("button", { name: /Shopping/ });
    expect(shopping).not.toHaveAttribute("aria-current");
    await userEvent.click(shopping);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Shopping" })).toBeInTheDocument());
    expect(shopping).toHaveAttribute("aria-current", "page");
  });

  it("creates a Grocy-owned chore from the dashboard form", async () => {
    const fetch = vi.fn(async (path: string, init?: RequestInit) => {
      if (path === "/api/v1/chore-users") return Response.json({ version: "1", state: "available", data: [{ id: "person-1", display_name: "Miguel" }], errors: [] });
      if (path === "/api/v1/chores" && init?.method === "POST") return Response.json({ version: "1", state: "available", data: snapshot.chores, errors: [] });
      return Response.json(envelope);
    });
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    await screen.findAllByText("Our Home");
    await userEvent.click(screen.getByRole("button", { name: /Chores/ }));
    await userEvent.click(screen.getByRole("button", { name: /Add chore/ }));
    await userEvent.type(screen.getByLabelText("Name"), "Water plants");
    await userEvent.click(screen.getByRole("button", { name: "Create chore" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/v1/chores",
      expect.objectContaining({ method: "POST" }),
    ));
    const createCall = fetch.mock.calls.find(([path, init]) => path === "/api/v1/chores" && init?.method === "POST");
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual(expect.objectContaining({ name: "Water plants", schedule_type: "weekly" }));
  });

  it("edits and safely deactivates chores without a delete action", async () => {
    const fetch = vi.fn(async (path: string, _init?: RequestInit) => {
      if (path === "/api/v1/chore-users") return Response.json({ version: "1", state: "available", data: [{ id: "person-1", display_name: "Miguel" }], errors: [] });
      return Response.json(envelope);
    });
    vi.stubGlobal("fetch", fetch);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);
    await screen.findAllByText("Our Home");
    await userEvent.click(screen.getByRole("button", { name: /Chores/ }));
    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(await screen.findByRole("heading", { name: "Edit chore" })).toBeInTheDocument();
    expect(screen.getByLabelText(/^Start date/)).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Deactivate" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/v1/chores/chore-1/deactivate",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(fetch.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(false);
  });
});

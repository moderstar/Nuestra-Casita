import type { ApiEnvelope, DashboardSnapshot, ShoppingProductOption } from "./types";

export class UnauthorizedError extends Error {
  constructor() {
    super("Your session has expired.");
    this.name = "UnauthorizedError";
  }
}

export class ApiRequestError extends Error {
  constructor(message = "Nuestra Casita is unavailable.") {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    const method = init?.method?.toUpperCase() ?? "GET";
    const csrf = document.cookie.split("; ").find((item) => item.startsWith("casita_csrf="))?.split("=").slice(1).join("=");
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set("Content-Type", "application/json");
    if (method !== "GET" && !(method === "POST" && path === "/api/v1/session")) {
      headers.set("X-CSRF-Token", decodeURIComponent(csrf ?? ""));
      headers.set("Idempotency-Key", crypto.randomUUID());
    }
    response = await fetch(path, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiRequestError();
  }
  if (response.status === 401) throw new UnauthorizedError();
  if (!response.ok) {
    let message = "Nuestra Casita is unavailable.";
    try {
      const payload = await response.json() as { detail?: string };
      if (typeof payload.detail === "string") message = payload.detail;
    } catch { /* Keep the safe fallback message. */ }
    throw new ApiRequestError(message);
  }
  return response;
}

export async function login(password: string): Promise<void> {
  await request("/api/v1/session", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export async function logout(): Promise<void> {
  await request("/api/v1/session", { method: "DELETE" });
}

export async function getDashboard(): Promise<ApiEnvelope<DashboardSnapshot>> {
  const response = await request("/api/v1/dashboard");
  const payload = (await response.json()) as ApiEnvelope<DashboardSnapshot>;
  if (payload.version !== "1" || !payload.data || !payload.data.household) {
    throw new ApiRequestError("The dashboard returned an unsupported response.");
  }
  return payload;
}

export async function searchShoppingProducts(query: string): Promise<ShoppingProductOption[]> {
  const response = await request(`/api/v1/shopping-products?query=${encodeURIComponent(query)}`);
  const payload = await response.json() as ApiEnvelope<ShoppingProductOption[]>;
  return payload.data;
}

export async function addShoppingItem(listId: string, input: { product_id: string | null; unit_id: string | null; quantity: string; note: string }): Promise<void> {
  await request(`/api/v1/shopping-lists/${encodeURIComponent(listId)}/items`, { method: "POST", body: JSON.stringify(input) });
}

export async function setShoppingItemPurchased(listId: string, itemId: string, purchased: boolean): Promise<void> {
  await request(`/api/v1/shopping-lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`, { method: "PUT", body: JSON.stringify({ purchased }) });
}

export async function removeShoppingItem(listId: string, itemId: string): Promise<void> {
  await request(`/api/v1/shopping-lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`, { method: "DELETE" });
}

export async function completeChore(choreId: string): Promise<void> {
  await request(`/api/v1/chores/${encodeURIComponent(choreId)}/complete`, { method: "POST" });
}

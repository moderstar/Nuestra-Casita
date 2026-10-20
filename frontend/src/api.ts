import type { ApiEnvelope, DashboardSnapshot } from "./types";

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
    response = await fetch(path, {
      ...init,
      credentials: "include",
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new ApiRequestError();
  }
  if (response.status === 401) throw new UnauthorizedError();
  if (!response.ok) throw new ApiRequestError();
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

import type { ApiEnvelope, DashboardSnapshot } from "../types";

export const snapshot: DashboardSnapshot = {
  contract_version: "1",
  generated_at: "2026-10-20T16:00:00+00:00",
  household: { id: "home", name: "Our Home", timezone: "America/Los_Angeles", members: [], source_references: [] },
  today: [],
  shopping_lists: [{ id: "list-1", household_id: "home", name: "Groceries", updated_at: null, items: [{ id: "item-1", name: "Milk", quantity: "2.00", unit: "cartons", checked: false, note: "" }] }],
  inventory: { household_id: "home", measured_at: null, items: [{ id: "stock-1", name: "Rice", quantity: "1.500", unit: "kg", location: "Pantry", expires_on: null, low_stock: false }] },
  recipes: [],
  chores: [],
  meal_plan: [],
  tasks: [],
  budget: null,
  devices: [],
  media: [],
  notifications: [],
  stale_sections: [],
  issues: [],
};

export const envelope: ApiEnvelope<DashboardSnapshot> = { version: "1", state: "available", data: snapshot, errors: [] };

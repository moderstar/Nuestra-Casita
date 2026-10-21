import type { ApiEnvelope, DashboardSnapshot } from "../types";

export const snapshot: DashboardSnapshot = {
  contract_version: "1",
  generated_at: "2026-10-20T16:00:00+00:00",
  household: { id: "home", name: "Our Home", timezone: "America/Los_Angeles", members: [], source_references: [] },
  today: [],
  shopping_lists: [{ id: "list-1", household_id: "home", name: "Groceries", updated_at: null, items: [{ id: "item-1", name: "Milk", quantity: "2.00", unit: "cartons", checked: false, note: "" }] }],
  inventory: { household_id: "home", measured_at: null, items: [{ id: "stock-1", name: "Rice", quantity: "1.500", unit: "kg", location: "Pantry", expires_on: null, low_stock: false }] },
  recipes: [],
  chores: [{
    id: "chore-1", household_id: "home", name: "Sweep kitchen",
    description: "After dinner", due_at: "2026-10-21T03:00:00+00:00",
    assigned_person_id: "person-1", assigned_person_name: "Miguel",
    completed: false, active: true, schedule_type: "weekly",
    schedule_interval: 1, schedule_day: 1, schedule_weekdays: ["monday"],
    start_at: "2026-10-20T15:00:00+00:00", start_at_editable: false,
    assignment_type: "in-alphabetical-order", assignment_user_ids: ["person-1"],
    assignment_user_names: ["Miguel"],
  }],
  meal_plan: [],
  tasks: [],
  budget: null,
  devices: [
    {
      id: "home-device-1", household_id: "home", name: "Kitchen Temperature",
      kind: "sensor", state: "available", value: "72.4", unit: "°F",
      attributes: [["device_class", "temperature"]],
      source_references: [{ integration: "home-assistant", external_id: "sensor.kitchen_temperature", external_type: "sensor" }],
    },
    {
      id: "home-device-2", household_id: "home", name: "Garage Door",
      kind: "binary_sensor", state: "unavailable", value: "unavailable", unit: "",
      attributes: [["device_class", "garage_door"]],
      source_references: [{ integration: "home-assistant", external_id: "binary_sensor.garage_door", external_type: "binary_sensor" }],
    },
    {
      id: "home-device-3", household_id: "home", name: "Weather Summary",
      kind: "sensor", state: "unknown", value: "unknown", unit: "",
      attributes: [],
      source_references: [{ integration: "home-assistant", external_id: "sensor.weather_summary", external_type: "sensor" }],
    },
  ],
  media: [],
  notifications: [],
  stale_sections: [],
  issues: [],
};

export const envelope: ApiEnvelope<DashboardSnapshot> = { version: "1", state: "available", data: snapshot, errors: [] };

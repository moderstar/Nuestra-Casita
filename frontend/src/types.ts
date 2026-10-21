export type ApiState = "available" | "empty" | "degraded";

export interface ApiError {
  code: string;
  source: string;
  capability: string;
  message: string;
}

export interface ApiEnvelope<T> {
  version: "1";
  state: ApiState;
  data: T;
  errors: ApiError[];
}

export interface SourceReference {
  integration: string;
  external_id: string;
  external_type: string;
}

export interface Household {
  id: string;
  name: string;
  timezone: string;
  members: string[];
  source_references: SourceReference[];
}

export interface CalendarEvent {
  id: string;
  household_id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  all_day: boolean;
  location: string;
  participant_ids: string[];
}

export interface ShoppingItem {
  id: string;
  name: string;
  quantity: string | null;
  unit: string;
  checked: boolean;
  note: string;
}

export interface ShoppingList {
  id: string;
  household_id: string;
  name: string;
  items: ShoppingItem[];
  updated_at: string | null;
}

export interface ShoppingProductOption {
  id: string;
  name: string;
  unit_id: string;
  unit: string;
}

export interface InventoryItem {
  id: string;
  name: string;
  quantity: string;
  unit: string;
  location: string;
  expires_on: string | null;
  low_stock: boolean;
}

export interface Inventory {
  household_id: string;
  items: InventoryItem[];
  measured_at: string | null;
}

export interface RecipeIngredient {
  name: string;
  quantity: string | null;
  unit: string;
  note: string;
}

export interface Recipe {
  id: string;
  household_id: string;
  name: string;
  description: string;
  servings: string;
  ingredients: RecipeIngredient[];
}

export interface Chore {
  id: string;
  household_id: string;
  name: string;
  description: string;
  due_at: string | null;
  assigned_person_id: string | null;
  assigned_person_name: string;
  completed: boolean;
  active: boolean;
  schedule_type: string;
  schedule_interval: number;
  schedule_day: number;
  schedule_weekdays: string[];
  start_at: string | null;
  start_at_editable: boolean;
  assignment_type: string;
  assignment_user_ids: string[];
  assignment_user_names: string[];
}

export interface ChoreUserOption {
  id: string;
  display_name: string;
}

export interface ChoreDefinitionInput {
  name: string;
  description: string;
  schedule_type: string;
  schedule_interval: number;
  schedule_day: number;
  schedule_weekdays: string[];
  start_at: string;
  assignment_type: string;
  assignment_user_ids: string[];
  active: boolean;
}

export type MealPlanEntryType = "recipe" | "product" | "note";

export interface MealPlanEntry {
  id: string;
  household_id: string;
  day: string;
  section: string;
  entry_type: MealPlanEntryType;
  title: string;
  description: string;
  servings: string | null;
  quantity: string | null;
  unit: string;
  completed: boolean;
  reference_available: boolean;
}

export interface HouseholdTask {
  id: string;
  household_id: string;
  name: string;
  description: string;
  due_on: string | null;
  category: string;
  completed: boolean;
}

export type DeviceAvailability = "available" | "unavailable" | "unknown";

export interface Device {
  id: string;
  household_id: string;
  name: string;
  kind: string;
  state: DeviceAvailability;
  value: string;
  unit: string;
  attributes: [string, string][];
  source_references: SourceReference[];
}

export interface DashboardSnapshot {
  contract_version: "1";
  generated_at: string;
  household: Household;
  today: CalendarEvent[];
  shopping_lists: ShoppingList[];
  inventory: Inventory | null;
  recipes: Recipe[];
  chores: Chore[];
  meal_plan: MealPlanEntry[];
  tasks: HouseholdTask[];
  budget: unknown | null;
  devices: Device[];
  media: unknown[];
  notifications: unknown[];
  stale_sections: string[];
  issues: ApiError[];
}

import { FormEvent, useEffect, useMemo, useState } from "react";
import { addShoppingItem, completeChore, createChore, deactivateChore, getChoreUsers, removeShoppingItem, searchShoppingProducts, setShoppingItemPurchased, updateChore } from "./api";
import { Card, EmptyState, ItemRow, PageHeading } from "./components";
import { formatDate, formatQuantity, isToday } from "./format";
import type { Chore, ChoreDefinitionInput, ChoreUserOption, DashboardSnapshot, MealPlanEntry, Recipe, ShoppingProductOption } from "./types";

interface PageProps { dashboard: DashboardSnapshot }
interface InteractivePageProps extends PageProps { onRefresh: () => Promise<void> }

const active = <span className="read-only-tag">Read only</span>;

function groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const group = key(item);
    groups.set(group, [...(groups.get(group) ?? []), item]);
  }
  return groups;
}

export function HomePage({ dashboard }: PageProps) {
  const shopping = dashboard.shopping_lists.flatMap((list) => list.items).filter((item) => !item.checked);
  const chores = dashboard.chores.filter((item) => !item.completed);
  const tasks = dashboard.tasks.filter((item) => !item.completed);
  const meals = dashboard.meal_plan.filter((item) => isToday(item.day));
  const inventory = dashboard.inventory?.items ?? [];
  return <>
    <PageHeading eyebrow="Household overview" title={`Welcome home`} detail="Everything your household needs today, in one calm place." />
    <div className="overview-strip">
      <div><span>Today</span><strong>{dashboard.today.length + meals.length}</strong><small>scheduled items</small></div>
      <div><span>Shopping</span><strong>{shopping.length}</strong><small>items remaining</small></div>
      <div><span>To do</span><strong>{chores.length + tasks.length}</strong><small>open chores & tasks</small></div>
      <div><span>Low stock</span><strong>{inventory.filter((item) => item.low_stock).length}</strong><small>inventory items</small></div>
    </div>
    <div className="widget-grid">
      <Card title="Today" icon="home" className="wide-card">
        {!dashboard.today.length && !meals.length ? <EmptyState title="A clear day" detail="No activities or meals are scheduled for today." /> : <div className="row-list">
          {dashboard.today.slice(0, 3).map((event) => <ItemRow key={event.id} title={event.title} detail={event.location} meta={event.all_day ? "All day" : formatDate(event.starts_at, { hour: "numeric", minute: "2-digit" })} />)}
          {meals.slice(0, 3).map((meal) => <ItemRow key={meal.id} title={meal.title || meal.description || "Planned meal"} detail={meal.section} meta={meal.entry_type} completed={meal.completed} />)}
        </div>}
      </Card>
      <Card title="Shopping" icon="cart" action={<strong className="card-count">{shopping.length}</strong>}>
        {!shopping.length ? <EmptyState title="Nothing to pick up" detail="Your active shopping lists are clear." /> : <div className="row-list">{shopping.slice(0, 4).map((item) => <ItemRow key={item.id} title={item.name} meta={formatQuantity(item.quantity, item.unit)} />)}</div>}
      </Card>
      <Card title="Upcoming chores" icon="chores" action={<strong className="card-count">{chores.length}</strong>}>
        {!chores.length ? <EmptyState title="All caught up" detail="There are no open chores right now." /> : <div className="row-list">{chores.slice(0, 4).map((chore) => <ItemRow key={chore.id} title={chore.name} meta={formatDate(chore.due_at)} />)}</div>}
      </Card>
      <Card title="Inventory" icon="box" action={<strong className="card-count">{inventory.length}</strong>}>
        {!inventory.length ? <EmptyState title="No inventory to show" detail="Inventory will appear when the connected backend returns it." /> : <div className="row-list">{inventory.filter((item) => item.low_stock).slice(0, 4).map((item) => <ItemRow key={item.id} title={item.name} meta={formatQuantity(item.quantity, item.unit)} warning />)}{!inventory.some((item) => item.low_stock) && <p className="all-good">Everything looks well stocked.</p>}</div>}
      </Card>
      <Card title="Open tasks" icon="tasks" action={<strong className="card-count">{tasks.length}</strong>}>
        {!tasks.length ? <EmptyState title="No open tasks" detail="Your household task list is clear." /> : <div className="row-list">{tasks.slice(0, 4).map((task) => <ItemRow key={task.id} title={task.name} detail={task.category} meta={formatDate(task.due_on)} />)}</div>}
      </Card>
    </div>
  </>;
}

function AddShoppingDialog({ lists, selectedListId, onClose, onSaved }: { lists: DashboardSnapshot["shopping_lists"]; selectedListId: string; onClose: () => void; onSaved: () => Promise<void> }) {
  const [listId, setListId] = useState(selectedListId);
  const [mode, setMode] = useState<"product" | "note">("product");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ShoppingProductOption[]>([]);
  const [product, setProduct] = useState<ShoppingProductOption | null>(null);
  const [note, setNote] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (mode !== "product" || query.trim().length < 1 || product) { setResults([]); return; }
    const timer = window.setTimeout(() => {
      void searchShoppingProducts(query).then(setResults).catch((reason: Error) => setError(reason.message));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [mode, query, product]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !listId || (mode === "product" ? !product : !note.trim())) return;
    setBusy(true); setError("");
    try {
      await addShoppingItem(listId, { product_id: mode === "product" ? product?.id ?? null : null, unit_id: mode === "product" ? product?.unit_id ?? null : null, quantity, note: mode === "note" ? note.trim() : note.trim() });
      await onSaved();
      onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The item could not be added."); }
    finally { setBusy(false); }
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="add-shopping-title">
    <header><div><span className="eyebrow">Live Grocy activity</span><h2 id="add-shopping-title">Add shopping item</h2></div><button className="close-button" type="button" onClick={onClose} aria-label="Close">×</button></header>
    <form onSubmit={submit}>
      <label>Shopping list<select value={listId} onChange={(event) => setListId(event.target.value)}>{lists.map((list) => <option value={list.id} key={list.id}>{list.name}</option>)}</select></label>
      <div className="segmented" role="group" aria-label="Item type"><button type="button" className={mode === "product" ? "selected" : ""} onClick={() => { setMode("product"); setProduct(null); }}>Product</button><button type="button" className={mode === "note" ? "selected" : ""} onClick={() => { setMode("note"); setProduct(null); }}>Free-text item</button></div>
      {mode === "product" ? <div className="product-search"><label>Product<input value={product?.name ?? query} onChange={(event) => { setProduct(null); setQuery(event.target.value); setError(""); }} maxLength={80} autoFocus placeholder="Search Grocy products" /></label>{results.length > 0 && <div className="search-results" role="listbox">{results.map((item) => <button type="button" key={item.id} onClick={() => { setProduct(item); setQuery(item.name); setResults([]); }}><strong>{item.name}</strong><span>{item.unit}</span></button>)}</div>}</div> : <label>Item description<input value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} autoFocus placeholder="What do you need?" /></label>}
      <div className="field-row"><label>Quantity<input type="number" min="0.000001" max="1000000" step="any" inputMode="decimal" value={quantity} onChange={(event) => setQuantity(event.target.value)} required /></label><label>Unit<input value={product?.unit ?? (mode === "note" ? "No unit" : "Select a product")} disabled /></label></div>
      {mode === "product" && <label>Note (optional)<input value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} /></label>}
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button compact" disabled={busy || !listId || (mode === "product" ? !product : !note.trim())}>{busy ? "Adding…" : "Add item"}</button></div>
    </form>
  </section></div>;
}

export function ShoppingPage({ dashboard, onRefresh }: InteractivePageProps) {
  const [selected, setSelected] = useState(dashboard.shopping_lists[0]?.id ?? "");
  const [adding, setAdding] = useState(false);
  const [busyItem, setBusyItem] = useState("");
  const [message, setMessage] = useState("");
  const list = dashboard.shopping_lists.find((item) => item.id === selected) ?? dashboard.shopping_lists[0];
  async function changeItem(itemId: string, operation: () => Promise<void>, success: string) {
    setBusyItem(itemId); setMessage("");
    try { await operation(); await onRefresh(); setMessage(success); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "The shopping list could not be changed."); }
    finally { setBusyItem(""); }
  }
  return <><PageHeading eyebrow="Groceries & errands" title="Shopping" detail="Live shopping activity from your connected household backend." action={dashboard.shopping_lists.length ? <button className="primary-button compact" onClick={() => setAdding(true)}>＋ Add item</button> : undefined} />
    {message && <p className="operation-message" role="status">{message}</p>}
    {!dashboard.shopping_lists.length ? <Card title="Shopping lists" icon="cart"><EmptyState title="No shopping lists" detail="Create a list in Grocy and it will appear here." /></Card> : <div className="split-layout">
      <nav className="list-selector" aria-label="Shopping lists">{dashboard.shopping_lists.map((entry) => <button key={entry.id} className={entry.id === list.id ? "selected" : ""} onClick={() => setSelected(entry.id)}><span>{entry.name}</span><strong>{entry.items.filter((item) => !item.checked).length}</strong></button>)}</nav>
      <Card title={list.name} icon="cart" action={<span className="muted">{list.items.length} items</span>}>
        {!list.items.length ? <EmptyState title="This list is empty" detail="Add a product or free-text item when you need it." /> : <div className="row-list spacious">{list.items.map((item) => <div className={`interactive-row${item.checked ? " completed" : ""}`} key={item.id}><button className="check-button" disabled={busyItem === item.id} aria-label={item.checked ? `Mark ${item.name} not purchased` : `Mark ${item.name} purchased`} onClick={() => void changeItem(item.id, () => setShoppingItemPurchased(list.id, item.id, !item.checked), item.checked ? "Item reopened." : "Item marked purchased.")}>{item.checked ? "✓" : ""}</button><div className="item-copy"><strong>{item.name}</strong>{item.note && <span>{item.note}</span>}</div><span className="item-meta">{formatQuantity(item.quantity, item.unit)}</span><button className="remove-button" disabled={busyItem === item.id} aria-label={`Remove ${item.name}`} onClick={() => { if (window.confirm(`Remove “${item.name}” from ${list.name}?`)) void changeItem(item.id, () => removeShoppingItem(list.id, item.id), "Item removed."); }}>Remove</button></div>)}</div>}
      </Card>
    </div>}{adding && <AddShoppingDialog lists={dashboard.shopping_lists} selectedListId={list.id} onClose={() => setAdding(false)} onSaved={onRefresh} />}
  </>;
}

export function InventoryPage({ dashboard }: PageProps) {
  const items = dashboard.inventory?.items ?? [];
  const grouped = useMemo(() => groupBy(items, (item) => item.location || "Household"), [items]);
  return <><PageHeading eyebrow="What we have" title="Inventory" detail="Current quantities, locations, and low-stock notices." action={active} />
    {!items.length ? <Card title="Inventory" icon="box"><EmptyState title="No inventory available" detail="Stock data will appear when the backend reports it." /></Card> : <div className="section-grid">{Array.from(grouped).map(([location, entries]) => <Card key={location} title={location} icon="box"><div className="row-list spacious">{entries.map((item) => <ItemRow key={item.id} title={item.name} detail={item.expires_on ? `Expires ${formatDate(item.expires_on)}` : undefined} meta={formatQuantity(item.quantity, item.unit)} warning={item.low_stock} />)}</div></Card>)}</div>}
  </>;
}

function RecipeDetails({ recipe }: { recipe: Recipe }) {
  return <div className="recipe-detail"><span className="eyebrow">{formatQuantity(recipe.servings)} servings</span><h2>{recipe.name}</h2>{recipe.description && <p>{recipe.description}</p>}<h3>Ingredients</h3>{recipe.ingredients.length ? <div className="row-list">{recipe.ingredients.map((ingredient, index) => <ItemRow key={`${ingredient.name}-${index}`} title={ingredient.name} detail={ingredient.note} meta={formatQuantity(ingredient.quantity, ingredient.unit)} />)}</div> : <EmptyState title="No ingredients available" detail="This recipe has no ingredient details in the current API response." />}</div>;
}

export function RecipesPage({ dashboard }: PageProps) {
  const [selected, setSelected] = useState(dashboard.recipes[0]?.id ?? "");
  const recipe = dashboard.recipes.find((item) => item.id === selected) ?? dashboard.recipes[0];
  return <><PageHeading eyebrow="From our kitchen" title="Recipes" detail="Browse household recipes and available ingredient details." action={active} />
    {!dashboard.recipes.length ? <Card title="Recipes" icon="book"><EmptyState title="No recipes available" detail="Recipes synchronized with the backend will appear here." /></Card> : <div className="split-layout recipes-layout"><nav className="list-selector" aria-label="Recipes">{dashboard.recipes.map((entry) => <button key={entry.id} className={entry.id === recipe.id ? "selected" : ""} onClick={() => setSelected(entry.id)}><span>{entry.name}</span><small>{formatQuantity(entry.servings)} servings</small></button>)}</nav><Card title="Recipe details" icon="book"><RecipeDetails recipe={recipe}/></Card></div>}
  </>;
}

export function MealPlanPage({ dashboard }: PageProps) {
  const grouped = groupBy(dashboard.meal_plan, (item) => item.day);
  return <><PageHeading eyebrow="This week at home" title="Meal plan" detail="Planned recipes, products, and notes organized by day." action={active} />
    {!dashboard.meal_plan.length ? <Card title="Meal plan" icon="meal"><EmptyState title="Nothing planned yet" detail="Meal plan entries from Grocy will appear here." /></Card> : <div className="day-grid">{Array.from(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([day, entries]) => <Card key={day} title={formatDate(day, { weekday: "long", month: "short", day: "numeric" })} className={isToday(day) ? "today-card" : ""}>{entries.map((entry: MealPlanEntry) => <ItemRow key={entry.id} title={entry.title || entry.description || "Unavailable reference"} detail={`${entry.section} · ${entry.entry_type}`} meta={entry.servings ? `${formatQuantity(entry.servings)} servings` : formatQuantity(entry.quantity, entry.unit)} completed={entry.completed} warning={!entry.reference_available} />)}</Card>)}</div>}
  </>;
}

const weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

function datetimeLocalValue(value?: string | null): string {
  const date = value ? new Date(value) : new Date();
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
}

function scheduleLabel(chore: Chore): string {
  if (chore.schedule_type === "manually") return "Manual";
  if (chore.schedule_type === "adaptive") return "Adaptive";
  if (chore.schedule_type === "weekly") return `Every ${chore.schedule_interval > 1 ? `${chore.schedule_interval} weeks · ` : "week · "}${chore.schedule_weekdays.map((day) => day.slice(0, 3)).join(", ")}`;
  if (chore.schedule_type === "monthly") return `Every ${chore.schedule_interval > 1 ? `${chore.schedule_interval} months` : "month"} · day ${chore.schedule_day}`;
  return `Every ${chore.schedule_interval > 1 ? `${chore.schedule_interval} ` : ""}${chore.schedule_type}${chore.schedule_interval > 1 ? "s" : ""}`;
}

function ChoreDialog({ chore, onClose, onSaved }: { chore: Chore | null; onClose: () => void; onSaved: () => Promise<void> }) {
  const [name, setName] = useState(chore?.name ?? "");
  const [description, setDescription] = useState(chore?.description ?? "");
  const [scheduleType, setScheduleType] = useState(chore?.schedule_type ?? "weekly");
  const [interval, setInterval] = useState(chore?.schedule_interval ?? 1);
  const [scheduleDay, setScheduleDay] = useState(chore?.schedule_day ?? 1);
  const [selectedDays, setSelectedDays] = useState<string[]>(chore?.schedule_weekdays ?? ["monday"]);
  const [startAt, setStartAt] = useState(datetimeLocalValue(chore?.start_at));
  const [assignmentType, setAssignmentType] = useState(chore?.assignment_type ?? "no-assignment");
  const [assignedUsers, setAssignedUsers] = useState<string[]>(chore?.assignment_user_ids ?? []);
  const [active, setActive] = useState(chore?.active ?? true);
  const [users, setUsers] = useState<ChoreUserOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void getChoreUsers().then(setUsers).catch((reason: Error) => setError(reason.message));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (scheduleType === "weekly" && !selectedDays.length) { setError("Choose at least one weekday."); return; }
    if (assignmentType !== "no-assignment" && !assignedUsers.length) { setError("Choose at least one person for this assignment mode."); return; }
    setBusy(true); setError("");
    const input: ChoreDefinitionInput = {
      name: name.trim(), description: description.trim(), schedule_type: scheduleType,
      schedule_interval: ["manually", "adaptive"].includes(scheduleType) ? 1 : interval,
      schedule_day: scheduleType === "monthly" ? scheduleDay : 1,
      schedule_weekdays: scheduleType === "weekly" ? weekdays.filter((day) => selectedDays.includes(day)) : [],
      start_at: new Date(startAt).toISOString(), assignment_type: assignmentType,
      assignment_user_ids: assignmentType === "no-assignment" ? [] : assignedUsers,
      active,
    };
    try {
      if (chore) await updateChore(chore.id, input); else await createChore(input);
      await onSaved(); onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The chore could not be saved."); }
    finally { setBusy(false); }
  }

  function toggleUser(id: string) {
    setAssignedUsers((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return <div className="modal-backdrop" role="presentation"><section className="modal chore-modal" role="dialog" aria-modal="true" aria-labelledby="chore-dialog-title"><header><div><span className="eyebrow">Grocy chore</span><h2 id="chore-dialog-title">{chore ? "Edit chore" : "Create chore"}</h2></div><button className="close-button" type="button" onClick={onClose} aria-label="Close">×</button></header><form onSubmit={submit}>
    <label>Name<input value={name} onChange={(event) => setName(event.target.value)} maxLength={100} required autoFocus /></label>
    <label>Description (optional)<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} rows={3} /></label>
    <div className="field-row"><label>Schedule<select value={scheduleType} onChange={(event) => setScheduleType(event.target.value)}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="manually">Manual</option><option value="hourly">Hourly</option><option value="yearly">Yearly</option><option value="adaptive">Adaptive</option></select></label>{!["manually", "adaptive"].includes(scheduleType) && <label>Repeat every<input type="number" min="1" max="10000" value={interval} onChange={(event) => setInterval(Number(event.target.value))} required /></label>}</div>
    {scheduleType === "weekly" && <fieldset className="choice-field"><legend>Weekdays</legend><div className="choice-grid">{weekdays.map((day) => <label key={day}><input type="checkbox" checked={selectedDays.includes(day)} onChange={() => setSelectedDays((current) => current.includes(day) ? current.filter((item) => item !== day) : [...current, day])} />{day.slice(0, 3)}</label>)}</div></fieldset>}
    {scheduleType === "monthly" && <label>Day of month<input type="number" min="1" max="31" value={scheduleDay} onChange={(event) => setScheduleDay(Number(event.target.value))} required /></label>}
    <label>Start date<input type="datetime-local" step="1" value={startAt} onChange={(event) => setStartAt(event.target.value)} disabled={chore ? !chore.start_at_editable : false} required />{chore && !chore.start_at_editable && <small>Grocy locks the start date after the first execution.</small>}</label>
    <label>Assignment<select value={assignmentType} onChange={(event) => { setAssignmentType(event.target.value); if (event.target.value === "no-assignment") setAssignedUsers([]); }}><option value="no-assignment">No assignment</option><option value="in-alphabetical-order">Rotate alphabetically</option><option value="who-least-did-first">Person with fewest completions</option><option value="random">Random rotation</option></select></label>
    {assignmentType !== "no-assignment" && <fieldset className="choice-field"><legend>Assign to</legend>{users.length ? <div className="choice-grid users">{users.map((user) => <label key={user.id}><input type="checkbox" checked={assignedUsers.includes(user.id)} onChange={() => toggleUser(user.id)} />{user.display_name}</label>)}</div> : <p className="muted">No assignable Grocy users are available.</p>}</fieldset>}
    <label className="toggle-label"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Active</label>
    {error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button compact" disabled={busy || !name.trim()}>{busy ? "Saving…" : chore ? "Save changes" : "Create chore"}</button></div>
  </form></section></div>;
}

export function ChoresPage({ dashboard, onRefresh }: InteractivePageProps) {
  const [busy, setBusy] = useState(""); const [message, setMessage] = useState(""); const [editing, setEditing] = useState<Chore | null | undefined>(undefined);
  async function finish(id: string) { setBusy(id); setMessage(""); try { await completeChore(id); await onRefresh(); setMessage("Chore completed."); } catch (reason) { setMessage(reason instanceof Error ? reason.message : "The chore could not be completed."); } finally { setBusy(""); } }
  async function deactivate(chore: Chore) { if (!window.confirm(`Deactivate “${chore.name}”? Its execution history will be preserved.`)) return; setBusy(chore.id); setMessage(""); try { await deactivateChore(chore.id); await onRefresh(); setMessage("Chore deactivated. Its history remains in Grocy."); } catch (reason) { setMessage(reason instanceof Error ? reason.message : "The chore could not be deactivated."); } finally { setBusy(""); } }
  return <><PageHeading eyebrow="Household rhythm" title="Chores" detail="Grocy-owned definitions, schedules, assignments, and completion history." action={<button className="primary-button compact" onClick={() => setEditing(null)}>＋ Add chore</button>} />{message && <p className="operation-message" role="status">{message}</p>}<Card title="Household chores" icon="chores" action={<span className="muted">{dashboard.chores.filter((item) => item.active).length} active · {dashboard.chores.length} total</span>}>{!dashboard.chores.length ? <EmptyState title="No chores available" detail="Create the first household chore here; it will be stored in Grocy." /> : <div className="row-list spacious">{dashboard.chores.map((chore) => <div className={`chore-management-row${!chore.active ? " inactive" : ""}`} key={chore.id}><span className="item-dot" /><div className="item-copy"><strong>{chore.name}{!chore.active && <small className="inactive-badge">Inactive</small>}</strong><span>{[chore.description, scheduleLabel(chore), chore.assigned_person_name || chore.assignment_user_names.join(", ")].filter(Boolean).join(" · ")}</span></div><span className="item-meta">{chore.active ? formatDate(chore.due_at) : "Not scheduled"}</span><div className="row-actions"><button className="secondary-button" disabled={busy === chore.id} onClick={() => setEditing(chore)}>Edit</button><button className="secondary-button" disabled={busy === chore.id || !chore.active} onClick={() => void finish(chore.id)}>{busy === chore.id ? "Saving…" : "Complete"}</button>{chore.active && <button className="remove-button" disabled={busy === chore.id} onClick={() => void deactivate(chore)}>Deactivate</button>}</div></div>)}</div>}</Card>{editing !== undefined && <ChoreDialog chore={editing} onClose={() => setEditing(undefined)} onSaved={onRefresh} />}</>;
}

export function TasksPage({ dashboard }: PageProps) {
  return <><PageHeading eyebrow="Things to remember" title="Tasks" detail="One-time household tasks, categories, and due dates." action={active} /><Card title="Household tasks" icon="tasks" action={<span className="muted">{dashboard.tasks.length} total</span>}>{!dashboard.tasks.length ? <EmptyState title="No tasks available" detail="Tasks from the connected backend will appear here." /> : <div className="row-list spacious">{dashboard.tasks.map((task) => <ItemRow key={task.id} title={task.name} detail={[task.description, task.category].filter(Boolean).join(" · ")} meta={formatDate(task.due_on)} completed={task.completed} />)}</div>}</Card></>;
}

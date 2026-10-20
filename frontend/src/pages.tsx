import { FormEvent, useEffect, useMemo, useState } from "react";
import { addShoppingItem, completeChore, removeShoppingItem, searchShoppingProducts, setShoppingItemPurchased } from "./api";
import { Card, EmptyState, ItemRow, PageHeading } from "./components";
import { formatDate, formatQuantity, isToday } from "./format";
import type { DashboardSnapshot, MealPlanEntry, Recipe, ShoppingProductOption } from "./types";

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

export function ChoresPage({ dashboard, onRefresh }: InteractivePageProps) {
  const [busy, setBusy] = useState(""); const [message, setMessage] = useState(""); const [showPolicy, setShowPolicy] = useState(false);
  async function finish(id: string) { setBusy(id); setMessage(""); try { await completeChore(id); await onRefresh(); setMessage("Chore completed."); } catch (reason) { setMessage(reason instanceof Error ? reason.message : "The chore could not be completed."); } finally { setBusy(""); } }
  return <><PageHeading eyebrow="Household rhythm" title="Chores" detail="Recurring household work and its current due status." action={<button className="secondary-button" onClick={() => setShowPolicy(true)}>＋ Add chore</button>} />{message && <p className="operation-message" role="status">{message}</p>}<Card title="Household chores" icon="chores" action={<span className="muted">{dashboard.chores.length} total</span>}>{!dashboard.chores.length ? <EmptyState title="No chores available" detail="Configured chores will appear here." /> : <div className="row-list spacious">{dashboard.chores.map((chore) => <div className={`interactive-row chore-row${chore.completed ? " completed" : ""}`} key={chore.id}><span className="item-dot">{chore.completed ? "✓" : ""}</span><div className="item-copy"><strong>{chore.name}</strong><span>{[chore.description, chore.assigned_person_id ? "Assigned" : ""].filter(Boolean).join(" · ")}</span></div><span className="item-meta">{formatDate(chore.due_at)}</span><button className="secondary-button row-action" disabled={busy === chore.id || chore.completed} onClick={() => void finish(chore.id)}>{busy === chore.id ? "Saving…" : chore.completed ? "Done" : "Complete"}</button></div>)}</div>}</Card>{showPolicy && <div className="modal-backdrop" role="presentation"><section className="modal compact-modal" role="dialog" aria-modal="true" aria-labelledby="chore-policy-title"><header><div><span className="eyebrow">Managed configuration</span><h2 id="chore-policy-title">Add a chore</h2></div><button className="close-button" onClick={() => setShowPolicy(false)} aria-label="Close">×</button></header><p>Chore definitions are managed in <code>catalog/chores.csv</code> so recurring schedules remain reproducible. Add the definition there, validate it, and use the existing synchronization command.</p><button className="primary-button compact" onClick={() => setShowPolicy(false)}>Got it</button></section></div>}</>;
}

export function TasksPage({ dashboard }: PageProps) {
  return <><PageHeading eyebrow="Things to remember" title="Tasks" detail="One-time household tasks, categories, and due dates." action={active} /><Card title="Household tasks" icon="tasks" action={<span className="muted">{dashboard.tasks.length} total</span>}>{!dashboard.tasks.length ? <EmptyState title="No tasks available" detail="Tasks from the connected backend will appear here." /> : <div className="row-list spacious">{dashboard.tasks.map((task) => <ItemRow key={task.id} title={task.name} detail={[task.description, task.category].filter(Boolean).join(" · ")} meta={formatDate(task.due_on)} completed={task.completed} />)}</div>}</Card></>;
}

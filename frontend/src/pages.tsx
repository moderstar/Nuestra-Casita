import { useMemo, useState } from "react";
import { Card, EmptyState, ItemRow, PageHeading } from "./components";
import { formatDate, formatQuantity, isToday } from "./format";
import type { DashboardSnapshot, MealPlanEntry, Recipe } from "./types";

interface PageProps { dashboard: DashboardSnapshot }

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

export function ShoppingPage({ dashboard }: PageProps) {
  const [selected, setSelected] = useState(dashboard.shopping_lists[0]?.id ?? "");
  const list = dashboard.shopping_lists.find((item) => item.id === selected) ?? dashboard.shopping_lists[0];
  return <><PageHeading eyebrow="Groceries & errands" title="Shopping" detail="Live shopping activity from your connected household backend." action={active} />
    {!dashboard.shopping_lists.length ? <Card title="Shopping lists" icon="cart"><EmptyState title="No shopping lists" detail="Create a list in Grocy and it will appear here." /></Card> : <div className="split-layout">
      <nav className="list-selector" aria-label="Shopping lists">{dashboard.shopping_lists.map((entry) => <button key={entry.id} className={entry.id === list.id ? "selected" : ""} onClick={() => setSelected(entry.id)}><span>{entry.name}</span><strong>{entry.items.filter((item) => !item.checked).length}</strong></button>)}</nav>
      <Card title={list.name} icon="cart" action={<span className="muted">{list.items.length} items</span>}>
        {!list.items.length ? <EmptyState title="This list is empty" detail="Items added in Grocy will appear here." /> : <div className="row-list spacious">{list.items.map((item) => <ItemRow key={item.id} title={item.name} detail={item.note} meta={formatQuantity(item.quantity, item.unit)} completed={item.checked} />)}</div>}
      </Card>
    </div>}
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

export function ChoresPage({ dashboard }: PageProps) {
  return <><PageHeading eyebrow="Household rhythm" title="Chores" detail="Recurring household work and its current due status." action={active} /><Card title="Household chores" icon="chores" action={<span className="muted">{dashboard.chores.length} total</span>}>{!dashboard.chores.length ? <EmptyState title="No chores available" detail="Configured chores will appear here." /> : <div className="row-list spacious">{dashboard.chores.map((chore) => <ItemRow key={chore.id} title={chore.name} detail={[chore.description, chore.assigned_person_id ? "Assigned" : ""].filter(Boolean).join(" · ")} meta={formatDate(chore.due_at)} completed={chore.completed} />)}</div>}</Card></>;
}

export function TasksPage({ dashboard }: PageProps) {
  return <><PageHeading eyebrow="Things to remember" title="Tasks" detail="One-time household tasks, categories, and due dates." action={active} /><Card title="Household tasks" icon="tasks" action={<span className="muted">{dashboard.tasks.length} total</span>}>{!dashboard.tasks.length ? <EmptyState title="No tasks available" detail="Tasks from the connected backend will appear here." /> : <div className="row-list spacious">{dashboard.tasks.map((task) => <ItemRow key={task.id} title={task.name} detail={[task.description, task.category].filter(Boolean).join(" · ")} meta={formatDate(task.due_on)} completed={task.completed} />)}</div>}</Card></>;
}

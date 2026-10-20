import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiRequestError, getDashboard, login, logout, UnauthorizedError } from "./api";
import { Icon, type IconName, StatusBadge } from "./components";
import { ChoresPage, HomePage, InventoryPage, MealPlanPage, RecipesPage, ShoppingPage, TasksPage } from "./pages";
import type { ApiEnvelope, DashboardSnapshot } from "./types";

type PageName = "home" | "shopping" | "inventory" | "recipes" | "meal-plan" | "chores" | "tasks";
type Theme = "system" | "light" | "dark";

const nav: { id: PageName; label: string; icon: IconName }[] = [
  { id: "home", label: "Home", icon: "home" },
  { id: "shopping", label: "Shopping", icon: "cart" },
  { id: "inventory", label: "Inventory", icon: "box" },
  { id: "recipes", label: "Recipes", icon: "book" },
  { id: "meal-plan", label: "Meal Plan", icon: "meal" },
  { id: "chores", label: "Chores", icon: "chores" },
  { id: "tasks", label: "Tasks", icon: "tasks" },
];

function LoginScreen({ onAuthenticated }: { onAuthenticated: () => Promise<void> }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!password) return;
    setBusy(true);
    setError("");
    try {
      await login(password);
      setPassword("");
      await onAuthenticated();
    } catch (reason) {
      setError(reason instanceof UnauthorizedError ? "That password wasn’t recognized." : "The dashboard could not be reached. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="login-shell">
    <div className="login-art" aria-hidden="true"><span className="house-mark">NC</span><div><strong>Nuestra Casita</strong><small>Our home, thoughtfully connected.</small></div></div>
    <section className="login-panel">
      <form className="login-card" onSubmit={submit}>
        <span className="eyebrow">Kitchen dashboard</span>
        <h1>Welcome home</h1>
        <p>Enter your household password to open the dashboard.</p>
        <label htmlFor="password">Household password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} autoFocus />
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="primary-button" disabled={busy || !password}>{busy ? "Opening…" : "Open dashboard"}</button>
        <small className="privacy-note">Your password is sent directly to Nuestra Casita and is never stored in this browser.</small>
      </form>
    </section>
  </main>;
}

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

function DashboardShell({ envelope, stale, refreshing, onRefresh, onLogout }: { envelope: ApiEnvelope<DashboardSnapshot>; stale: boolean; refreshing: boolean; onRefresh: () => void; onLogout: () => void }) {
  const [page, setPage] = useState<PageName>("home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>("system");
  const now = useClock();
  const dashboard = envelope.data;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const pages: Record<PageName, React.ReactNode> = {
    home: <HomePage dashboard={dashboard} />,
    shopping: <ShoppingPage dashboard={dashboard} />,
    inventory: <InventoryPage dashboard={dashboard} />,
    recipes: <RecipesPage dashboard={dashboard} />,
    "meal-plan": <MealPlanPage dashboard={dashboard} />,
    chores: <ChoresPage dashboard={dashboard} />,
    tasks: <TasksPage dashboard={dashboard} />,
  };

  function selectPage(next: PageName) {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="house-mark small">NC</span><div><strong>Nuestra Casita</strong><small>{dashboard.household.name}</small></div></div>
      <div className="topbar-center"><strong>{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(now)}</strong><span>{new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(now)}</span></div>
      <div className="topbar-actions">
        <StatusBadge state={envelope.state} stale={stale || dashboard.stale_sections.length > 0} />
        <button className="icon-button" aria-label="Refresh dashboard" onClick={onRefresh} disabled={refreshing}><Icon name="refresh"/><span className="desktop-only">{refreshing ? "Refreshing" : "Refresh"}</span></button>
        <div className="account-menu"><button className="icon-button" aria-label="Open settings" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}><Icon name="settings"/></button>{menuOpen && <div className="menu-popover">
          <span className="menu-label">Appearance</span>
          <div className="theme-options">{(["system", "light", "dark"] as Theme[]).map((item) => <button key={item} className={theme === item ? "active" : ""} onClick={() => setTheme(item)}>{item === "dark" ? <Icon name="moon" size={17}/> : <Icon name="sun" size={17}/>} {item}</button>)}</div>
          <button className="logout-button" onClick={onLogout}><Icon name="logout" size={18}/> Sign out</button>
        </div>}</div>
      </div>
    </header>
    {(envelope.state === "degraded" || stale || dashboard.stale_sections.length > 0) && <div className="degraded-banner" role="status"><Icon name="wifi" size={19}/><span><strong>Some information may be out of date.</strong> Previously loaded data remains visible while the connection recovers.</span></div>}
    <nav className="primary-nav" aria-label="Primary navigation">{nav.map((item) => <button key={item.id} aria-current={page === item.id ? "page" : undefined} onClick={() => selectPage(item.id)}><Icon name={item.icon}/><span>{item.label}</span></button>)}</nav>
    <main className="content" id="main-content">{pages[page]}</main>
    <footer className="footer"><span>Updated {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(dashboard.generated_at))}</span><span>Dashboard contract v{dashboard.contract_version}</span></footer>
  </div>;
}

export default function App() {
  const [dashboard, setDashboard] = useState<ApiEnvelope<DashboardSnapshot> | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [stale, setStale] = useState(false);
  const refreshRef = useRef<() => Promise<void>>(async () => undefined);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const next = await getDashboard();
      setDashboard(next);
      setAuthenticated(true);
      setStale(false);
    } catch (reason) {
      if (reason instanceof UnauthorizedError) {
        setAuthenticated(false);
        setDashboard(null);
      } else if (reason instanceof ApiRequestError) {
        setStale(true);
        setAuthenticated((current) => current ?? false);
      }
    } finally {
      setRefreshing(false);
    }
  }, []);
  refreshRef.current = refresh;

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshRef.current();
    }, 60_000);
    const visible = () => { if (document.visibilityState === "visible") void refreshRef.current(); };
    document.addEventListener("visibilitychange", visible);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", visible); };
  }, []);

  async function signOut() {
    try { await logout(); } catch { /* A failed logout still clears local authenticated state. */ }
    setDashboard(null);
    setAuthenticated(false);
  }

  if (authenticated === null) return <main className="boot-screen"><span className="house-mark">NC</span><p>Opening Nuestra Casita…</p></main>;
  if (!authenticated || !dashboard) return <LoginScreen onAuthenticated={refresh} />;
  return <DashboardShell envelope={dashboard} stale={stale} refreshing={refreshing} onRefresh={() => void refresh()} onLogout={() => void signOut()} />;
}

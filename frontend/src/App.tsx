import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiRequestError, getDashboard, getDevices, login, logout, UnauthorizedError } from "./api";
import { Icon, type IconName, StatusBadge } from "./components";
import { HomeAssistantEntityManager } from "./HomeAssistantEntityManager";
import { ChoresPage, HomePage, HomeStatusPage, InventoryPage, MealPlanPage, RecipesPage, ShoppingPage, TasksPage } from "./pages";
import type { ApiEnvelope, DashboardSnapshot } from "./types";

type PageName = "home" | "home-status" | "home-assistant-settings" | "shopping" | "inventory" | "recipes" | "meal-plan" | "chores" | "tasks";
type Theme = "system" | "light" | "dark";

const nav: { id: PageName; label: string; icon: IconName }[] = [
  { id: "home", label: "Home", icon: "home" },
  { id: "home-status", label: "Home Status", icon: "status" },
  { id: "shopping", label: "Shopping", icon: "cart" },
  { id: "inventory", label: "Inventory", icon: "box" },
  { id: "recipes", label: "Recipes", icon: "book" },
  { id: "meal-plan", label: "Meal Plan", icon: "meal" },
  { id: "chores", label: "Chores", icon: "chores" },
  { id: "tasks", label: "Tasks", icon: "tasks" },
];

export const DASHBOARD_POLL_INTERVAL_MS = 30_000;
export const DEVICE_POLL_INTERVAL_MS = 10_000;

const pagePaths: Record<PageName, string> = {
  home: "/",
  "home-status": "/home-status",
  "home-assistant-settings": "/settings/home-assistant",
  shopping: "/shopping",
  inventory: "/inventory",
  recipes: "/recipes",
  "meal-plan": "/meal-plan",
  chores: "/chores",
  tasks: "/tasks",
};

function pageFromPath(pathname: string): PageName | null {
  const normalized = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return (Object.entries(pagePaths).find(([, path]) => path === normalized)?.[0] as PageName | undefined) ?? null;
}

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

function DashboardShell({ envelope, stale, refreshing, onRefresh, onLogout }: { envelope: ApiEnvelope<DashboardSnapshot>; stale: boolean; refreshing: boolean; onRefresh: () => Promise<void>; onLogout: () => void }) {
  const [page, setPage] = useState<PageName>(() => pageFromPath(window.location.pathname) ?? "home");
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>("system");
  const now = useClock();
  const dashboard = envelope.data;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!pageFromPath(window.location.pathname)) window.history.replaceState({}, "", pagePaths.home);
    const navigateFromHistory = () => {
      const next = pageFromPath(window.location.pathname) ?? "home";
      if (!pageFromPath(window.location.pathname)) window.history.replaceState({}, "", pagePaths.home);
      setPage(next);
      window.scrollTo({ top: 0, behavior: "smooth" });
    };
    window.addEventListener("popstate", navigateFromHistory);
    return () => window.removeEventListener("popstate", navigateFromHistory);
  }, []);

  const pages: Record<PageName, React.ReactNode> = {
    home: <HomePage dashboard={dashboard} />,
    "home-status": <HomeStatusPage dashboard={dashboard} onManageEntities={() => selectPage("home-assistant-settings")} />,
    "home-assistant-settings": <HomeAssistantEntityManager />,
    shopping: <ShoppingPage dashboard={dashboard} onRefresh={onRefresh} />,
    inventory: <InventoryPage dashboard={dashboard} />,
    recipes: <RecipesPage dashboard={dashboard} />,
    "meal-plan": <MealPlanPage dashboard={dashboard} />,
    chores: <ChoresPage dashboard={dashboard} onRefresh={onRefresh} />,
    tasks: <TasksPage dashboard={dashboard} />,
  };

  function selectPage(next: PageName) {
    if (window.location.pathname !== pagePaths[next]) window.history.pushState({}, "", pagePaths[next]);
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="house-mark small">NC</span><div><strong>Nuestra Casita</strong><small>{dashboard.household.name}</small></div></div>
      <div className="topbar-center"><strong>{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(now)}</strong><span>{new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(now)}</span></div>
      <div className="topbar-actions">
        <StatusBadge state={envelope.state} stale={stale || dashboard.stale_sections.length > 0} />
        <button className="icon-button" aria-label="Refresh dashboard" onClick={() => void onRefresh()} disabled={refreshing}><Icon name="refresh"/><span className="desktop-only">{refreshing ? "Refreshing" : "Refresh"}</span></button>
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
  const dashboardRef = useRef<ApiEnvelope<DashboardSnapshot> | null>(null);
  const authenticatedRef = useRef<boolean | null>(null);
  const sequenceRef = useRef(0);
  const fullAppliedSequenceRef = useRef(0);
  const deviceAppliedSequenceRef = useRef(0);
  const fullRequestRef = useRef<{ controller: AbortController; promise: Promise<void> } | null>(null);
  const deviceRequestRef = useRef<{ controller: AbortController; promise: Promise<void> } | null>(null);

  const commitDashboard = useCallback((next: ApiEnvelope<DashboardSnapshot>) => {
    dashboardRef.current = next;
    setDashboard(next);
  }, []);

  const expireSession = useCallback(() => {
    fullRequestRef.current?.controller.abort();
    deviceRequestRef.current?.controller.abort();
    dashboardRef.current = null;
    authenticatedRef.current = false;
    setDashboard(null);
    setAuthenticated(false);
  }, []);

  const refreshDashboard = useCallback((interactive = false): Promise<void> => {
    const active = fullRequestRef.current;
    if (active) {
      if (interactive) {
        setRefreshing(true);
        void active.promise.finally(() => setRefreshing(false));
      }
      return active.promise;
    }

    const controller = new AbortController();
    const sequence = ++sequenceRef.current;
    if (interactive) setRefreshing(true);
    const promise = (async () => {
      try {
        const next = await getDashboard(controller.signal);
        if (controller.signal.aborted || sequence <= fullAppliedSequenceRef.current) return;
        fullAppliedSequenceRef.current = sequence;
        const current = dashboardRef.current;
        const data = { ...next.data };
        if (current) {
          const preservedSections: Record<string, keyof DashboardSnapshot> = {
            today: "today", shopping: "shopping_lists", inventory: "inventory", recipes: "recipes",
            chores: "chores", "meal-plan": "meal_plan", tasks: "tasks", budget: "budget",
            home: "devices", media: "media", notifications: "notifications",
          };
          for (const section of next.data.stale_sections) {
            const field = preservedSections[section];
            if (field) (data as unknown as Record<string, unknown>)[field] = current.data[field];
          }
          if (deviceAppliedSequenceRef.current > sequence) data.devices = current.data.devices;
        }
        commitDashboard({ ...next, data });
        authenticatedRef.current = true;
        setAuthenticated(true);
        setStale(false);
      } catch (reason) {
        if (controller.signal.aborted) return;
        if (reason instanceof UnauthorizedError) expireSession();
        else if (reason instanceof ApiRequestError) {
          setStale(true);
          setAuthenticated((current) => current ?? false);
        }
      } finally {
        if (fullRequestRef.current?.controller === controller) fullRequestRef.current = null;
        if (interactive) setRefreshing(false);
      }
    })();
    fullRequestRef.current = { controller, promise };
    return promise;
  }, [commitDashboard, expireSession]);

  const refreshDevices = useCallback((): Promise<void> => {
    if (authenticatedRef.current !== true || !dashboardRef.current) return Promise.resolve();
    if (deviceRequestRef.current) return deviceRequestRef.current.promise;

    const controller = new AbortController();
    const sequence = ++sequenceRef.current;
    const promise = (async () => {
      try {
        const next = await getDevices(controller.signal);
        if (controller.signal.aborted || sequence <= deviceAppliedSequenceRef.current || sequence < fullAppliedSequenceRef.current) return;
        deviceAppliedSequenceRef.current = sequence;
        const current = dashboardRef.current;
        if (!current) return;
        const failed = next.state === "degraded" || next.errors.length > 0;
        const errors = [
          ...current.errors.filter((error) => error.capability !== "devices"),
          ...(failed ? next.errors : []),
        ];
        const staleSections = failed
          ? Array.from(new Set([...current.data.stale_sections, "home"]))
          : current.data.stale_sections.filter((section) => section !== "home");
        commitDashboard({
          ...current,
          state: errors.length || staleSections.length ? "degraded" : "available",
          errors,
          data: {
            ...current.data,
            devices: failed ? current.data.devices : next.data,
            stale_sections: staleSections,
            issues: errors,
          },
        });
      } catch (reason) {
        if (controller.signal.aborted) return;
        if (reason instanceof UnauthorizedError) expireSession();
        else if (reason instanceof ApiRequestError) {
          const current = dashboardRef.current;
          if (current) commitDashboard({
            ...current,
            state: "degraded",
            data: { ...current.data, stale_sections: Array.from(new Set([...current.data.stale_sections, "home"])) },
          });
        }
      } finally {
        if (deviceRequestRef.current?.controller === controller) deviceRequestRef.current = null;
      }
    })();
    deviceRequestRef.current = { controller, promise };
    return promise;
  }, [commitDashboard, expireSession]);

  const refresh = useCallback(() => refreshDashboard(true), [refreshDashboard]);

  useEffect(() => { void refreshDashboard(false); }, [refreshDashboard]);
  useEffect(() => {
    const dashboardTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshDashboard(false);
    }, DASHBOARD_POLL_INTERVAL_MS);
    const deviceTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshDevices();
    }, DEVICE_POLL_INTERVAL_MS);
    const visible = () => {
      if (document.visibilityState !== "visible") return;
      void refreshDashboard(false);
      void refreshDevices();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      window.clearInterval(dashboardTimer);
      window.clearInterval(deviceTimer);
      document.removeEventListener("visibilitychange", visible);
      fullRequestRef.current?.controller.abort();
      deviceRequestRef.current?.controller.abort();
    };
  }, [refreshDashboard, refreshDevices]);

  async function signOut() {
    try { await logout(); } catch { /* A failed logout still clears local authenticated state. */ }
    fullRequestRef.current?.controller.abort();
    deviceRequestRef.current?.controller.abort();
    dashboardRef.current = null;
    authenticatedRef.current = false;
    setDashboard(null);
    setAuthenticated(false);
  }

  if (authenticated === null) return <main className="boot-screen"><span className="house-mark">NC</span><p>Opening Nuestra Casita…</p></main>;
  if (!authenticated || !dashboard) return <LoginScreen onAuthenticated={refresh} />;
  return <DashboardShell envelope={dashboard} stale={stale} refreshing={refreshing} onRefresh={refresh} onLogout={() => void signOut()} />;
}

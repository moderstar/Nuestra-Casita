import type { PropsWithChildren, ReactNode } from "react";
import type { ApiState } from "./types";

export type IconName = "home" | "cart" | "box" | "book" | "meal" | "chores" | "tasks" | "status" | "refresh" | "settings" | "moon" | "sun" | "logout" | "wifi";

const paths: Record<IconName, ReactNode> = {
  home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>,
  cart: <><path d="M3 4h2l2.2 10h9.9l2-7H6"/><circle cx="9" cy="19" r="1"/><circle cx="17" cy="19" r="1"/></>,
  box: <><path d="m4 7 8-4 8 4-8 4Z"/><path d="M4 7v10l8 4 8-4V7M12 11v10"/></>,
  book: <><path d="M4 4h6a2 2 0 0 1 2 2v14a3 3 0 0 0-3-3H4Z"/><path d="M20 4h-6a2 2 0 0 0-2 2v14a3 3 0 0 1 3-3h5Z"/></>,
  meal: <><path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M16 3v18M16 3c5 3 5 9 0 11"/></>,
  chores: <><path d="M9 4h6M9 2v4M5 7h14l-1 14H6Z"/><path d="M9 11v6M15 11v6"/></>,
  tasks: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8 9 2 2 4-4M8 16h8"/></>,
  status: <><path d="M4 13a8 8 0 0 1 16 0"/><path d="M7 13a5 5 0 0 1 10 0"/><circle cx="12" cy="13" r="2"/><path d="M12 15v6"/></>,
  refresh: <><path d="M20 6v5h-5M4 18v-5h5"/><path d="M18 10a7 7 0 0 0-12-3L4 11M6 14a7 7 0 0 0 12 3l2-4"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a2 2 0 0 0 .4 2.2l.1.1-2.6 2.6-.1-.1A2 2 0 0 0 15 19.4a2 2 0 0 0-1.2 1.8V21h-3.6v-.2A2 2 0 0 0 9 19.4a2 2 0 0 0-2.2.4l-.1.1-2.6-2.6.1-.1A2 2 0 0 0 4.6 15a2 2 0 0 0-1.8-1.2H3v-3.6h.2A2 2 0 0 0 4.6 9a2 2 0 0 0-.4-2.2l-.1-.1 2.6-2.6.1.1A2 2 0 0 0 9 4.6a2 2 0 0 0 1.2-1.8V3h3.6v.2A2 2 0 0 0 15 4.6a2 2 0 0 0 2.2-.4l.1-.1 2.6 2.6-.1.1A2 2 0 0 0 19.4 9a2 2 0 0 0 1.8 1.2h.2v3.6h-.2A2 2 0 0 0 19.4 15Z"/></>,
  moon: <path d="M20 15a8 8 0 0 1-11-11 8 8 0 1 0 11 11Z"/>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
  logout: <><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9"/></>,
  wifi: <><path d="M5 12.6a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="20" r="1"/></>,
};

export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  return <svg aria-hidden="true" className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

export function Card({ title, icon, action, className = "", children }: PropsWithChildren<{ title: string; icon?: IconName; action?: ReactNode; className?: string }>) {
  return <section className={`card ${className}`}>
    <header className="card-header"><h2>{icon && <Icon name={icon} size={20}/>} {title}</h2>{action}</header>
    <div className="card-body">{children}</div>
  </section>;
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><span className="empty-mark" aria-hidden="true">✦</span><strong>{title}</strong><p>{detail}</p></div>;
}

export function StatusBadge({ state, stale = false }: { state: ApiState; stale?: boolean }) {
  const status = stale ? "stale" : state;
  return <span className={`status-badge ${status}`}><span aria-hidden="true" />{status === "available" ? "Connected" : status === "empty" ? "Up to date" : status === "stale" ? "Stale data" : "Limited"}</span>;
}

export function ItemRow({ title, meta, detail, completed = false, warning = false }: { title: string; meta?: string; detail?: string; completed?: boolean; warning?: boolean }) {
  return <div className={`item-row${completed ? " completed" : ""}`}>
    <span className={`item-dot${warning ? " warning" : ""}`} aria-hidden="true">{completed ? "✓" : ""}</span>
    <div className="item-copy"><strong>{title}</strong>{detail && <span>{detail}</span>}</div>
    {meta && <span className="item-meta">{meta}</span>}
  </div>;
}

export function PageHeading({ eyebrow, title, detail, action }: { eyebrow?: string; title: string; detail: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{detail}</p></div>{action}</div>;
}

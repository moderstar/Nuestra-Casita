export function formatQuantity(value: string | null, unit = ""): string {
  if (value === null || value === "") return unit;
  const numeric = Number(value);
  const quantity = Number.isFinite(numeric)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(numeric)
    : value;
  return [quantity, unit].filter(Boolean).join(" ");
}

export function formatDate(value: string | null, options?: Intl.DateTimeFormatOptions): string {
  if (!value) return "No due date";
  const date = new Date(value.includes("T") ? value : `${value}T12:00:00`);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat(undefined, options ?? { month: "short", day: "numeric" }).format(date);
}

export function isToday(value: string): boolean {
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  const now = new Date();
  return date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate();
}

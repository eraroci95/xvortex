// Amounts arrive as decimal strings from the API; they are only converted for display.
export function formatMoney(value: string | number, currency?: string | null): string {
  const n = Number(value);
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currency ?? "SEK" }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency ?? ""}`.trim();
  }
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
}

export const isNegative = (value: string): boolean => Number(value) < 0;

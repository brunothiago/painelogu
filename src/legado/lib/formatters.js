export function parseDate(v) {
  if (!v) return null;
  const d = new Date(`${v}T12:00:00Z`);
  return isNaN(d) ? null : d;
}

/** Soma dias corridos em calendário (UTC), preservando o horário de referência. */
export function addCalendarDays(date, days) {
  if (!(date instanceof Date) || isNaN(date)) return null;
  const out = new Date(date.getTime());
  out.setUTCDate(out.getUTCDate() + days);
  return out;
}

const numberFormatter = new Intl.NumberFormat("pt-BR");
const currencyCompactFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const percentFormatter = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatNumber(value) {
  return numberFormatter.format(value ?? 0);
}

export function formatCurrencyCompact(value) {
  return currencyCompactFormatter.format(value ?? 0);
}

export function formatPercent(value) {
  return percentFormatter.format(value ?? 0);
}

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "UTC",
});

export function formatDate(value) {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(`${value}T12:00:00Z`);
  return isNaN(d) ? "—" : dateFormatter.format(d);
}

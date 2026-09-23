import type { Money } from "@/lib/project-data";

const numberFormat = new Intl.NumberFormat("en-IE");
const dateFormat = new Intl.DateTimeFormat("en-IE", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export const formatNumber = (value: number) => numberFormat.format(value);

export const formatDate = (value: string) =>
  dateFormat.format(new Date(`${value}T00:00:00Z`));

export const formatOptionalDate = (value: string | null) =>
  value ? formatDate(value) : "Not recorded";

export const formatPercent = (basisPoints: number) => `${(basisPoints / 100).toFixed(2)}%`;

export const formatMoney = (money: Money) =>
  new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: money.currency,
    currencyDisplay: "narrowSymbol",
  }).format(money.minorUnits / 100);

export const titleCase = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

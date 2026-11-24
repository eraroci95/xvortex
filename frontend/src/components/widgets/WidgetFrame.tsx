import type { ReactNode } from "react";

export function WidgetFrame({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="glass flex min-h-[14rem] flex-col rounded-2xl p-5" aria-label={title}>
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-semibold">{title}</h2>
        {aside}
      </header>
      <div className="flex-1">{children}</div>
    </section>
  );
}

export function Row({ label, value, tone }: { label: string; value: ReactNode; tone?: "danger" | "good" }) {
  const color = tone === "danger" ? "text-danger" : tone === "good" ? "text-cyan" : "";
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <dt className="text-dim">{label}</dt>
      <dd className={`num ${color}`}>{value}</dd>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-dim">{children}</p>;
}

export function Unavailable({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-dim" role="note">{children}</p>
  );
}

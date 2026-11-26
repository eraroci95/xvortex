import { useState, type PointerEvent } from "react";
import { formatDate } from "../../lib/format";
import type { DailyPrices } from "../../lib/types";

const W = 720;
const PAD = { l: 56, r: 12, t: 12, b: 22 };
const num = (v: string | null): number | null => (v === null ? null : Number(v));

interface Series { key: string; label: string; color: string; dash?: string; values: (number | null)[] }

function path(values: (number | null)[], x: (i: number) => number, y: (v: number) => number): string {
  let d = "";
  let pen = false;
  values.forEach((v, i) => {
    if (v === null) { pen = false; return; }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

function Panel({
  height, series, hover, setHover, dates, guides, fixed, format,
}: {
  height: number; series: Series[]; hover: number | null; setHover: (i: number | null) => void; dates: string[];
  guides?: number[]; fixed?: [number, number]; format: (v: number) => string;
}) {
  const n = dates.length;
  const all = series.flatMap((s) => s.values).filter((v): v is number => v !== null);
  let lo = fixed ? fixed[0] : Math.min(...all);
  let hi = fixed ? fixed[1] : Math.max(...all);
  if (lo === hi) { lo -= 1; hi += 1; }
  const x = (i: number) => PAD.l + (n === 1 ? 0 : (i / (n - 1)) * (W - PAD.l - PAD.r));
  const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (height - PAD.t - PAD.b);
  const ticks = [lo, lo + (hi - lo) / 2, hi];

  function move(e: PointerEvent<SVGRectElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * (W - PAD.l - PAD.r);
    setHover(Math.max(0, Math.min(n - 1, Math.round((px / (W - PAD.l - PAD.r)) * (n - 1)))));
  }

  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="w-full" role="img" aria-label={series.map((s) => s.label).join(", ")}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="rgb(var(--line) / 0.12)" />
          <text x={PAD.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="rgb(var(--dim))">{format(t)}</text>
        </g>
      ))}
      {guides?.map((g) => (
        <line key={g} x1={PAD.l} x2={W - PAD.r} y1={y(g)} y2={y(g)} stroke="rgb(var(--dim) / 0.5)" strokeDasharray="2 4" />
      ))}
      <text x={PAD.l} y={height - 6} fontSize="11" fill="rgb(var(--dim))">{formatDate(dates[0], "UTC")}</text>
      <text x={W - PAD.r} y={height - 6} textAnchor="end" fontSize="11" fill="rgb(var(--dim))">{formatDate(dates[n - 1], "UTC")}</text>
      {series.map((s) => (
        <path key={s.key} d={path(s.values, x, y)} fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dash}
          strokeLinecap="round" strokeLinejoin="round" />
      ))}
      {hover !== null && (
        <g>
          <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={height - PAD.b} stroke="rgb(var(--dim) / 0.6)" />
          {series.map((s) => s.values[hover] !== null && (
            <circle key={s.key} cx={x(hover)} cy={y(s.values[hover] as number)} r={4} fill={s.color} stroke="rgb(var(--panel))" strokeWidth={2} />
          ))}
        </g>
      )}
      <rect x={PAD.l} y={PAD.t} width={W - PAD.l - PAD.r} height={height - PAD.t - PAD.b} fill="transparent"
        onPointerMove={move} onPointerLeave={() => setHover(null)} />
    </svg>
  );
}

export function PriceChart({ data, currencyHint }: { data: DailyPrices; currencyHint?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const [asTable, setAsTable] = useState(false);
  const dates = data.bars.map((b) => b.date);
  const price: Series[] = [
    { key: "close", label: "Close", color: "rgb(var(--chart-1))", values: data.bars.map((b) => Number(b.close)) },
    { key: "sma20", label: "20-day average", color: "rgb(var(--chart-2))", dash: "6 4", values: data.sma20.map(num) },
    { key: "sma50", label: "50-day average", color: "rgb(var(--chart-3))", dash: "2 4", values: data.sma50.map(num) },
  ].filter((s) => s.values.some((v) => v !== null));
  const rsi: Series[] = [{ key: "rsi", label: "RSI (14)", color: "rgb(var(--chart-1))", values: data.rsi14.map(num) }];
  const i = hover ?? data.bars.length - 1;
  const bar = data.bars[i];
  const fmt = (v: number) => v.toFixed(2);

  if (data.bars.length < 2) return <p className="text-sm text-dim">Not enough prices to draw a chart.</p>;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ul className="flex flex-wrap gap-4 text-xs" aria-label="Legend">
          {price.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <svg width="26" height="8" aria-hidden><line x1="0" x2="26" y1="4" y2="4" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash} /></svg>
              {s.label}
            </li>
          ))}
        </ul>
        <button className="btn btn-ghost" onClick={() => setAsTable((t) => !t)}>{asTable ? "Show chart" : "Show as table"}</button>
      </div>

      <p className="num mt-2 text-sm" aria-live="off">
        {formatDate(bar.date, "UTC")} · close {bar.close}{currencyHint ? ` ${currencyHint}` : ""}
        {data.sma20[i] && ` · 20-day ${fmt(Number(data.sma20[i]))}`}
        {data.sma50[i] && ` · 50-day ${fmt(Number(data.sma50[i]))}`}
        {data.rsi14[i] && ` · RSI ${fmt(Number(data.rsi14[i]))}`}
      </p>

      {asTable ? (
        <div className="mt-3 max-h-80 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-panel text-xs uppercase tracking-wide text-dim">
              <tr><th className="py-1 pr-3">Date</th><th className="pr-3 text-right">Open</th><th className="pr-3 text-right">High</th>
                <th className="pr-3 text-right">Low</th><th className="pr-3 text-right">Close</th><th className="pr-3 text-right">20-day</th>
                <th className="pr-3 text-right">50-day</th><th className="text-right">RSI</th></tr>
            </thead>
            <tbody>
              {[...data.bars.keys()].reverse().map((k) => {
                const b = data.bars[k];
                return (
                  <tr key={b.date} className="border-t border-line/15 num">
                    <td className="py-1 pr-3">{b.date}</td><td className="pr-3 text-right">{b.open}</td><td className="pr-3 text-right">{b.high}</td>
                    <td className="pr-3 text-right">{b.low}</td><td className="pr-3 text-right">{b.close}</td>
                    <td className="pr-3 text-right">{data.sma20[k] ?? "—"}</td><td className="pr-3 text-right">{data.sma50[k] ?? "—"}</td>
                    <td className="text-right">{data.rsi14[k] ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          <div className="mt-2"><Panel height={260} series={price} hover={hover} setHover={setHover} dates={dates} format={fmt} /></div>
          <p className="mt-3 text-xs text-dim">RSI (14): above 70 is often read as stretched upward, below 30 as stretched downward. It describes past moves only.</p>
          <div className="mt-1">
            <Panel height={110} series={rsi} hover={hover} setHover={setHover} dates={dates} guides={[30, 70]} fixed={[0, 100]} format={(v) => v.toFixed(0)} />
          </div>
        </>
      )}
    </div>
  );
}

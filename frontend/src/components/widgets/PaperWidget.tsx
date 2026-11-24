import { Link } from "react-router-dom";
import { formatMoney, isNegative } from "../../lib/format";
import type { DashboardSummary } from "../../lib/types";
import { Empty, Row, Unavailable, WidgetFrame } from "./WidgetFrame";

export function PaperWidget({ data }: { data: DashboardSummary }) {
  const p = data.paper;
  return (
    <WidgetFrame
      title="Paper trading"
      aside={<span className="rounded-full border border-violet/40 px-2 py-0.5 text-xs text-violet">Simulated</span>}
    >
      {p.accounts === 0 ? (
        <Empty>
          No paper trading account yet. Create one in <Link className="text-cyan hover:underline" to="/paper">Paper Trading</Link> to
          practise with virtual cash. No real orders are ever placed.
        </Empty>
      ) : (
        <>
          <p className="text-sm text-dim">Available virtual cash</p>
          <p className="num mt-1 text-2xl font-medium">{formatMoney(p.cash, p.currency)}</p>
          <dl className="mt-3 divide-y divide-white/5">
            <Row label="Invested, at cost" value={formatMoney(p.invested_at_cost, p.currency)} />
            <Row label="Realized profit/loss" value={formatMoney(p.realized_pnl, p.currency)}
              tone={isNegative(p.realized_pnl) ? "danger" : Number(p.realized_pnl) > 0 ? "good" : undefined} />
            <Row label="Starting cash" value={formatMoney(p.starting_cash, p.currency)} />
          </dl>
          {p.valuation_status === "unavailable" && (
            <div className="mt-3">
              <Unavailable>
                Portfolio value and unrealized profit/loss need live prices, which are not connected yet.
                Invested amounts are shown at purchase cost.
              </Unavailable>
            </div>
          )}
        </>
      )}
    </WidgetFrame>
  );
}

import { Link } from "react-router-dom";
import type { DashboardSummary } from "../../lib/types";
import { Empty, Unavailable, WidgetFrame } from "./WidgetFrame";

export function MarketWidget({ data }: { data: DashboardSummary }) {
  return (
    <WidgetFrame title="Market watch" aside={<Link className="text-sm text-cyan hover:underline" to="/market">Open market</Link>}>
      {data.watchlists.length === 0 ? (
        <Empty>No watchlists yet. Create one in Market to track instruments.</Empty>
      ) : (
        <ul className="space-y-3">
          {data.watchlists.map((w) => (
            <li key={w.id}>
              <p className="text-sm font-medium">{w.name} <span className="text-dim">({w.symbol_count})</span></p>
              <p className="num mt-1 text-sm text-dim">{w.symbols.join("  ") || "No instruments"}</p>
            </li>
          ))}
        </ul>
      )}
      {data.market_data_status === "end_of_day" && data.watchlists.length > 0 && (
        <p className="mt-4 text-xs text-dim">Prices are end-of-day. Open Market to see the latest saved close for each symbol.</p>
      )}
      {data.market_data_status === "unavailable" && (
        <div className="mt-4">
          <Unavailable>No price source is connected yet, so quotes and daily changes are not shown.</Unavailable>
        </div>
      )}
    </WidgetFrame>
  );
}

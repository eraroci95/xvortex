import { formatDate, formatMoney } from "../../lib/format";
import type { DashboardSummary } from "../../lib/types";
import { Empty, WidgetFrame } from "./WidgetFrame";

export function TransactionsWidget({ data }: { data: DashboardSummary }) {
  return (
    <WidgetFrame title="Recent transactions">
      {data.transactions.length === 0 ? (
        <Empty>Nothing yet. Loan payments and simulated trades will be listed here.</Empty>
      ) : (
        <ul className="divide-y divide-white/5">
          {data.transactions.map((t, i) => (
            <li key={`${t.occurred_at}-${i}`} className="flex items-center justify-between gap-3 py-2 text-sm">
              <div className="min-w-0">
                <p className="truncate">
                  {t.label}
                  {t.simulated && <span className="ml-2 rounded-full border border-violet/40 px-1.5 py-0.5 text-xs text-violet">Simulated</span>}
                </p>
                <p className="text-xs text-dim">{formatDate(t.occurred_at)}</p>
              </div>
              <span className="num shrink-0">{formatMoney(t.amount, t.currency)}</span>
            </li>
          ))}
        </ul>
      )}
    </WidgetFrame>
  );
}

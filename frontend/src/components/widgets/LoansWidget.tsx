import { Link } from "react-router-dom";
import { formatMoney } from "../../lib/format";
import type { DashboardSummary } from "../../lib/types";
import { Empty, Row, WidgetFrame } from "./WidgetFrame";

export function LoansWidget({ data }: { data: DashboardSummary }) {
  const { loans } = data;
  return (
    <WidgetFrame title="Loans" aside={<Link className="text-sm text-cyan hover:underline" to="/loans">Open loans</Link>}>
      {loans.length === 0 ? (
        <Empty>No active loans yet. Add a borrower and a loan to see totals here.</Empty>
      ) : (
        <div className="space-y-5">
          {loans.map((t) => (
            <div key={t.currency}>
              <p className="text-sm text-dim">Outstanding principal{loans.length > 1 ? ` (${t.currency})` : ""}</p>
              <p className="num mt-1 text-2xl font-medium">{formatMoney(t.outstanding_principal, t.currency)}</p>
              <dl className="mt-3 divide-y divide-white/5">
                <Row label="Remaining interest" value={formatMoney(t.remaining_interest, t.currency)} />
                <Row label="Total lent" value={formatMoney(t.total_lent, t.currency)} />
                <Row label="Active loans" value={t.active_loans} />
                <Row label="Overdue loans" value={t.overdue_loans} tone={t.overdue_loans > 0 ? "danger" : undefined} />
                {t.overdue_loans > 0 && (
                  <Row label="Amount overdue" value={formatMoney(t.overdue_amount, t.currency)} tone="danger" />
                )}
              </dl>
            </div>
          ))}
        </div>
      )}
    </WidgetFrame>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Users } from "lucide-react";
import { RiskBadge, StatusBadge } from "../components/loans/labels";
import { formatDate, formatMoney } from "../lib/format";
import type { LoanSummary } from "../lib/types";
import { useApi } from "../lib/useApi";

const VIEWS = [
  { id: "active", label: "Active" },
  { id: "finished", label: "Repaid and closed" },
  { id: "archived", label: "Archived" },
] as const;

type View = (typeof VIEWS)[number]["id"];

export default function Loans() {
  const [view, setView] = useState<View>("active");
  const { data, error, loading } = useApi<LoanSummary[]>(`/api/loans?view=${view}`);

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Loans</h1>
        <div className="flex gap-2">
          <Link to="/loans/borrowers" className="btn btn-ghost"><Users className="h-4 w-4" aria-hidden />Borrowers</Link>
          <Link to="/loans/new" className="btn btn-primary"><Plus className="h-4 w-4" aria-hidden />New loan</Link>
        </div>
      </div>

      <div role="tablist" aria-label="Loan view" className="mt-5 flex gap-1 border-b border-line/20">
        {VIEWS.map((v) => (
          <button key={v.id} role="tab" aria-selected={view === v.id} onClick={() => setView(v.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${view === v.id ? "border-cyan text-fg" : "border-transparent text-dim hover:text-fg"}`}>
            {v.label}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-6 text-sm text-danger">{error}</p>}
      {loading && !data && <p className="mt-6 text-sm text-dim" role="status">Loading loans…</p>}
      {data && data.length === 0 && (
        <div className="glass mt-6 rounded-2xl p-6 text-sm text-dim">
          {view === "active"
            ? <>No active loans yet. <Link to="/loans/new" className="text-cyan underline">Add your first loan</Link>; you will need a borrower first.</>
            : "Nothing here."}
        </div>
      )}
      {data && data.length > 0 && (
        <div className="glass mt-6 overflow-x-auto rounded-2xl p-2">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-dim">
              <tr>
                <th className="px-3 py-2 font-medium">Borrower</th>
                <th className="px-3 py-2 text-right font-medium">Principal</th>
                <th className="px-3 py-2 text-right font-medium">Outstanding</th>
                <th className="px-3 py-2 font-medium">Next payment</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {data.map((l) => (
                <tr key={l.id} className="border-t border-line/15 hover:bg-line/5">
                  <td className="px-3 py-3">
                    <Link to={`/loans/${l.id}`} className="font-medium text-cyan hover:underline">{l.borrower_name}</Link>
                    <div className="text-xs text-dim">{formatDate(l.start_date, "UTC")} to {formatDate(l.maturity_date, "UTC")}</div>
                  </td>
                  <td className="px-3 py-3 text-right num">{formatMoney(l.principal, l.currency)}</td>
                  <td className="px-3 py-3 text-right num">{formatMoney(l.outstanding_principal, l.currency)}</td>
                  <td className="px-3 py-3">
                    {l.next_due_date && l.next_due_amount ? (
                      <>
                        <span className="num">{formatMoney(l.next_due_amount, l.currency)}</span>
                        <div className="text-xs text-dim">{formatDate(l.next_due_date, "UTC")}</div>
                      </>
                    ) : <span className="text-dim">—</span>}
                    {l.overdue_installments > 0 && (
                      <div className="text-xs text-danger">{l.overdue_installments} overdue · {formatMoney(l.overdue_amount, l.currency)}</div>
                    )}
                  </td>
                  <td className="px-3 py-3"><StatusBadge status={l.status} archived={l.archived} /></td>
                  <td className="px-3 py-3"><RiskBadge risk={l.risk} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-4 text-xs text-dim">Amounts in different currencies are never added together.</p>
    </section>
  );
}

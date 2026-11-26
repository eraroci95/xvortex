import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { FREQUENCY_LABEL, METHOD_LABEL, RiskBadge, StatusBadge } from "../components/loans/labels";
import { ScheduleTable } from "../components/loans/ScheduleTable";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import type { LoanDetail as Loan } from "../lib/types";
import { useApi } from "../lib/useApi";

const today = () => new Date().toISOString().slice(0, 10);
const message = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Try again.");

function Stat({ label, value, tone }: { label: string; value: string; tone?: "bad" }) {
  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-xs uppercase tracking-wide text-dim">{label}</p>
      <p className={`mt-1 text-lg num ${tone === "bad" ? "text-danger" : ""}`}>{value}</p>
    </div>
  );
}

export default function LoanDetail() {
  const { id = "" } = useParams();
  const { data, error, loading, reload } = useApi<Loan>(`/api/loans/${id}`);
  // After a change the server returns the fresh loan, which replaces what useApi loaded.
  const [loan, setLoan] = useState<Loan | null>(null);
  useEffect(() => { if (data) setLoan(data); }, [data]);

  const [paidOn, setPaidOn] = useState(today());
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [notes, setNotes] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<Loan>): Promise<boolean> {
    setBusy(true);
    setActionError(null);
    try {
      setLoan(await fn());
      return true;
    } catch (err) {
      setActionError(message(err));
      if (err instanceof ApiError && err.status === 404) reload();
      return false;
    } finally {
      setBusy(false);
    }
  }

  const patch = (body: Record<string, unknown>) => run(() => api<Loan>(`/api/loans/${id}`, { method: "PATCH", body }));

  async function addPayment(e: FormEvent) {
    e.preventDefault();
    const ok = await run(() => api<Loan>(`/api/loans/${id}/payments`, {
      method: "POST", body: { paid_on: paidOn, amount, note },
    }));
    if (ok) { setAmount(""); setNote(""); }
  }

  async function removePayment(paymentId: string, label: string) {
    if (!window.confirm(`Delete the payment of ${label}? Balances and the loan status are recalculated.`)) return;
    await run(() => api<Loan>(`/api/loans/${id}/payments/${paymentId}`, { method: "DELETE" }));
  }

  if (error && !loan) {
    return (
      <section>
        <Link to="/loans" className="text-sm text-dim hover:text-fg">Back to loans</Link>
        <p role="alert" className="mt-4 text-sm text-danger">{error}</p>
      </section>
    );
  }
  if (!loan) return <p className="text-sm text-dim" role="status">{loading ? "Loading loan…" : ""}</p>;

  const cur = loan.currency;
  const canPay = loan.status === "active";
  const notesDirty = notes !== null && notes !== (loan.notes ?? "");

  return (
    <section>
      <Link to="/loans" className="inline-flex items-center gap-1 text-sm text-dim hover:text-fg">
        <ArrowLeft className="h-4 w-4" aria-hidden />Loans
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{loan.borrower_name}</h1>
        <StatusBadge status={loan.status} archived={loan.archived} />
        <RiskBadge risk={loan.risk} />
      </div>
      <p className="mt-1 text-sm text-dim">
        {formatMoney(loan.principal, cur)} at {Number(loan.annual_interest_rate)}% a year · {FREQUENCY_LABEL[loan.repayment_frequency]} ·{" "}
        {METHOD_LABEL[loan.amortization_method]} · {formatDate(loan.start_date, "UTC")} to {formatDate(loan.maturity_date, "UTC")}
      </p>

      {actionError && <p role="alert" className="mt-4 text-sm text-danger">{actionError}</p>}

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Principal outstanding" value={formatMoney(loan.outstanding_principal, cur)} />
        <Stat label="Interest still to come" value={formatMoney(loan.remaining_interest, cur)} />
        <Stat label="Paid so far" value={formatMoney(loan.total_paid, cur)} />
        <Stat label="Overdue" value={loan.overdue_installments ? `${formatMoney(loan.overdue_amount, cur)} (${loan.overdue_installments})` : "None"}
          tone={loan.overdue_installments ? "bad" : undefined} />
      </div>
      {Number(loan.unapplied_payments) > 0 && (
        <p className="mt-3 text-sm text-dim">Paid beyond the schedule: {formatMoney(loan.unapplied_payments, cur)}.</p>
      )}

      {loan.risk && loan.risk.triggers.length > 0 && (
        <div className="glass mt-6 rounded-2xl p-5">
          <h2 className="font-semibold">Why this loan is flagged</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{loan.risk.triggers.map((t) => <li key={t}>{t}</li>)}</ul>
          <p className="mt-3 text-xs text-dim">{loan.risk.disclaimer}</p>
        </div>
      )}

      <div className="glass mt-6 rounded-2xl p-6">
        <h2 className="font-semibold">Payments</h2>
        {canPay ? (
          <form onSubmit={(e) => void addPayment(e)} className="mt-4 grid gap-4 sm:grid-cols-4">
            <Field label="Date received" type="date" required min={loan.start_date} max={today()} value={paidOn} onChange={(e) => setPaidOn(e.target.value)} />
            <Field label="Amount" required inputMode="decimal" pattern="[0-9]+([.][0-9]{1,2})?" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <Field label="Note (optional)" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
            <div className="flex items-end">
              <button className="btn btn-primary w-full" disabled={busy || !amount || !paidOn}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}Record payment
              </button>
            </div>
          </form>
        ) : (
          <p className="mt-2 text-sm text-dim">Payments can only be recorded on active loans.</p>
        )}
        {loan.payments.length === 0 ? (
          <p className="mt-4 text-sm text-dim">No payments recorded yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-line/15 text-sm">
            {loan.payments.map((p) => {
              const label = formatMoney(p.amount, cur);
              return (
                <li key={p.id} className="flex items-center justify-between gap-3 py-2">
                  <span>{formatDate(p.paid_on, "UTC")}{p.note && <span className="ml-2 text-dim">{p.note}</span>}</span>
                  <span className="flex items-center gap-3">
                    <span className="num">{label}</span>
                    <button className="text-dim hover:text-danger" aria-label={`Delete payment of ${label} on ${formatDate(p.paid_on, "UTC")}`}
                      disabled={busy} onClick={() => void removePayment(p.id, label)}>
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="glass mt-6 rounded-2xl p-6">
        <h2 className="font-semibold">Schedule</h2>
        <div className="mt-3"><ScheduleTable rows={loan.schedule} currency={cur} showProgress /></div>
        <p className="mt-3 text-xs text-dim">
          Payments are applied to the oldest unpaid installment first, interest before principal. Remaining interest is not
          recalculated after an early repayment.
        </p>
      </div>

      <div className="glass mt-6 rounded-2xl p-6">
        <h2 className="font-semibold">Notes and status</h2>
        <label htmlFor="loan-notes" className="sr-only">Notes</label>
        <textarea id="loan-notes" className="field mt-3 min-h-24" maxLength={5000}
          value={notes ?? loan.notes ?? ""} onChange={(e) => setNotes(e.target.value)} />
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="btn btn-ghost" disabled={busy || !notesDirty}
            onClick={() => void patch({ notes: notes ?? "" }).then((ok) => ok && setNotes(null))}>Save notes</button>
          {loan.status !== "closed" && (
            <button className="btn btn-ghost" disabled={busy}
              onClick={() => window.confirm("Close this loan? No more payments can be recorded until you reopen it.") && void patch({ status: "closed" })}>
              Close loan
            </button>
          )}
          {loan.status === "closed" && <button className="btn btn-ghost" disabled={busy} onClick={() => void patch({ status: "active" })}>Reopen loan</button>}
          {loan.status !== "active" && !loan.archived && <button className="btn btn-ghost" disabled={busy} onClick={() => void patch({ archived: true })}>Archive</button>}
          {loan.archived && <button className="btn btn-ghost" disabled={busy} onClick={() => void patch({ archived: false })}>Restore from archive</button>}
        </div>
      </div>
    </section>
  );
}

import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { FREQUENCY_LABEL, METHOD_LABEL } from "../components/loans/labels";
import { ScheduleTable } from "../components/loans/ScheduleTable";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { Borrower, Frequency, LoanDetail, LoanPreview, Method } from "../lib/types";
import { useApi } from "../lib/useApi";

const today = () => new Date().toISOString().slice(0, 10);

export default function NewLoan() {
  const navigate = useNavigate();
  const { data: borrowers, error: loadError } = useApi<Borrower[]>("/api/borrowers");
  const [borrowerId, setBorrowerId] = useState("");
  const [principal, setPrincipal] = useState("");
  const [rate, setRate] = useState("");
  const [currency, setCurrency] = useState("SEK");
  const [start, setStart] = useState(today());
  const [maturity, setMaturity] = useState("");
  const [frequency, setFrequency] = useState<Frequency>("monthly");
  const [method, setMethod] = useState<Method>("annuity");
  const [notes, setNotes] = useState("");
  const [preview, setPreview] = useState<LoanPreview | null>(null);
  const [previewKey, setPreviewKey] = useState("");
  const [busy, setBusy] = useState<"preview" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const terms = useMemo(() => ({
    principal, annual_interest_rate: rate, currency: currency.toUpperCase(), start_date: start, maturity_date: maturity,
    repayment_frequency: frequency, amortization_method: method,
  }), [principal, rate, currency, start, maturity, frequency, method]);
  const termsKey = JSON.stringify(terms);
  const complete = Boolean(principal && rate !== "" && start && maturity && currency.length === 3);
  // A preview only counts while the form still matches it.
  const previewIsCurrent = preview !== null && previewKey === termsKey;

  async function runPreview() {
    setBusy("preview");
    setError(null);
    try {
      setPreview(await api<LoanPreview>("/api/loans/preview", { method: "POST", body: terms }));
      setPreviewKey(termsKey);
    } catch (err) {
      setPreview(null);
      setError(err instanceof ApiError ? err.message : "Could not build the schedule.");
    } finally {
      setBusy(null);
    }
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!previewIsCurrent) { await runPreview(); return; }
    setBusy("save");
    setError(null);
    try {
      const loan = await api<LoanDetail>("/api/loans", { method: "POST", body: { ...terms, borrower_id: borrowerId, notes } });
      navigate(`/loans/${loan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the loan.");
      setBusy(null);
    }
  }

  return (
    <section>
      <Link to="/loans" className="inline-flex items-center gap-1 text-sm text-dim hover:text-fg">
        <ArrowLeft className="h-4 w-4" aria-hidden />Loans
      </Link>
      <h1 className="mt-2 text-2xl font-semibold">New loan</h1>

      {loadError && <p role="alert" className="mt-4 text-sm text-danger">{loadError}</p>}
      {borrowers && borrowers.length === 0 && (
        <p className="glass mt-6 rounded-2xl p-6 text-sm">
          You need a borrower first. <Link to="/loans/borrowers" className="text-cyan underline">Add one</Link>, then come back.
        </p>
      )}

      {borrowers && borrowers.length > 0 && (
        <form onSubmit={(e) => void save(e)} className="glass mt-6 rounded-2xl p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="borrower" className="mb-1.5 block text-sm font-medium">Borrower</label>
              <select id="borrower" className="field" required value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)}>
                <option value="">Choose a borrower</option>
                {borrowers.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            <Field label="Currency" required maxLength={3} minLength={3} pattern="[A-Za-z]{3}" hint="Three letters, for example SEK or USD."
              value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
            <Field label="Amount lent" required inputMode="decimal" pattern="[0-9]+([.][0-9]{1,2})?" hint="Up to two decimals."
              value={principal} onChange={(e) => setPrincipal(e.target.value)} />
            <Field label="Yearly interest rate (%)" required inputMode="decimal" pattern="[0-9]+([.][0-9]{1,4})?"
              hint="0 for an interest-free loan."
              value={rate} onChange={(e) => setRate(e.target.value)} />
            <Field label="Start date" type="date" required value={start} onChange={(e) => setStart(e.target.value)} />
            <Field label="Final payment date" type="date" required min={start} value={maturity} onChange={(e) => setMaturity(e.target.value)} />
            <div>
              <label htmlFor="frequency" className="mb-1.5 block text-sm font-medium">Repayment frequency</label>
              <select id="frequency" className="field" value={frequency} onChange={(e) => setFrequency(e.target.value as Frequency)}>
                {(Object.keys(FREQUENCY_LABEL) as Frequency[]).map((f) => <option key={f} value={f}>{FREQUENCY_LABEL[f]}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="method" className="mb-1.5 block text-sm font-medium">Repayment method</label>
              <select id="method" className="field" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
                {(Object.keys(METHOD_LABEL) as Method[]).map((m) => <option key={m} value={m}>{METHOD_LABEL[m]}</option>)}
              </select>
            </div>
            <Field className="sm:col-span-2" label="Notes (optional)" maxLength={5000} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>

          {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
          <div className="mt-6 flex flex-wrap gap-2">
            <button type="button" className="btn btn-ghost" disabled={!complete || busy !== null} onClick={() => void runPreview()}>
              {busy === "preview" && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}Preview schedule
            </button>
            <button className="btn btn-primary" disabled={!complete || !borrowerId || busy !== null}>
              {busy === "save" && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {previewIsCurrent ? "Save loan" : "Preview, then save"}
            </button>
          </div>
        </form>
      )}

      {preview && (
        <div className="glass mt-6 rounded-2xl p-6" aria-live="polite">
          <h2 className="font-semibold">Repayment schedule</h2>
          {!previewIsCurrent && <p className="mt-1 text-sm text-amber-500">The form changed since this preview. Preview again before saving.</p>}
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <div><dt className="text-dim">Principal</dt><dd className="num">{formatMoney(preview.total_principal, currency)}</dd></div>
            <div><dt className="text-dim">Total interest</dt><dd className="num">{formatMoney(preview.total_interest, currency)}</dd></div>
            <div><dt className="text-dim">Total to be repaid</dt><dd className="num">{formatMoney(preview.total_repayable, currency)}</dd></div>
          </dl>
          <div className="mt-4"><ScheduleTable rows={preview.installments} currency={currency} showProgress={false} /></div>
          <p className="mt-3 text-xs text-dim">
            Interest uses the yearly rate divided by the number of periods per year. Early repayments reduce what is owed on the
            oldest installments; the schedule is not recalculated.
          </p>
        </div>
      )}
    </section>
  );
}

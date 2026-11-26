import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import type { Borrower } from "../lib/types";
import { useApi } from "../lib/useApi";

const message = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Try again.");

function BorrowerForm({
  initial, submitLabel, onSubmit, onCancel,
}: {
  initial?: Borrower;
  submitLabel: string;
  onSubmit: (v: { name: string; email: string; phone: string; notes: string }) => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit({ name, email, phone, notes });
      if (!initial) { setName(""); setEmail(""); setPhone(""); setNotes(""); }
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="grid gap-4 sm:grid-cols-2">
      <Field label="Name" required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
      <Field label="Email (optional)" type="email" maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} />
      <Field label="Phone (optional)" maxLength={50} value={phone} onChange={(e) => setPhone(e.target.value)} />
      <Field label="Notes (optional)" maxLength={5000} value={notes} onChange={(e) => setNotes(e.target.value)} />
      {error && <p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>}
      <div className="flex gap-2 sm:col-span-2">
        <button className="btn btn-primary" disabled={busy || !name.trim()}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{submitLabel}
        </button>
        {onCancel && <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

export default function Borrowers() {
  const [showArchived, setShowArchived] = useState(false);
  const { data, error, loading, reload } = useApi<Borrower[]>(`/api/borrowers?include_archived=${showArchived}`);
  const [editing, setEditing] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function add(v: { name: string; email: string; phone: string; notes: string }) {
    await api("/api/borrowers", { method: "POST", body: v });
    reload();
  }

  async function patch(id: string, body: Record<string, unknown>) {
    setActionError(null);
    try {
      await api(`/api/borrowers/${id}`, { method: "PATCH", body });
      setEditing(null);
      reload();
    } catch (err) {
      setActionError(message(err));
      throw err;
    }
  }

  return (
    <section>
      <Link to="/loans" className="inline-flex items-center gap-1 text-sm text-dim hover:text-fg">
        <ArrowLeft className="h-4 w-4" aria-hidden />Loans
      </Link>
      <h1 className="mt-2 text-2xl font-semibold">Borrowers</h1>

      <div className="glass mt-6 rounded-2xl p-6">
        <h2 className="mb-4 font-semibold">Add a borrower</h2>
        <BorrowerForm submitLabel="Add borrower" onSubmit={add} />
      </div>

      <label className="mt-6 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
        Show archived borrowers
      </label>
      {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
      {actionError && <p role="alert" className="mt-4 text-sm text-danger">{actionError}</p>}
      {loading && !data && <p className="mt-4 text-sm text-dim" role="status">Loading…</p>}
      {data && data.length === 0 && <p className="mt-4 text-sm text-dim">No borrowers yet.</p>}

      <ul className="mt-4 space-y-3">
        {data?.map((b) => (
          <li key={b.id} className="glass rounded-2xl p-5">
            {editing === b.id ? (
              <BorrowerForm initial={b} submitLabel="Save"
                onSubmit={(v) => patch(b.id, v)} onCancel={() => setEditing(null)} />
            ) : (
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{b.name}{b.archived && <span className="ml-2 text-xs text-dim">(archived)</span>}</p>
                  <p className="text-sm text-dim">
                    {[b.email, b.phone].filter(Boolean).join(" · ") || "No contact details"}
                  </p>
                  {b.notes && <p className="mt-1 text-sm">{b.notes}</p>}
                  <p className="mt-1 text-xs text-dim">{b.loan_count} loan{b.loan_count === 1 ? "" : "s"}, {b.active_loan_count} active</p>
                </div>
                <div className="flex gap-2">
                  <button className="btn btn-ghost" onClick={() => setEditing(b.id)}>Edit</button>
                  <button className="btn btn-ghost" onClick={() => void patch(b.id, { archived: !b.archived }).catch(() => undefined)}>
                    {b.archived ? "Restore" : "Archive"}
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

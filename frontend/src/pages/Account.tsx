import { useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Field } from "../components/ui/Field";
import { api, ApiError, setCsrfToken } from "../lib/api";
import { MIN_PASSWORD_LENGTH } from "../lib/password";

export default function Account() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(false);
    if (next !== repeat) {
      setError("The new password and its repeat do not match.");
      return;
    }
    setBusy(true);
    try {
      // The server replaces every session, this one included, and returns the new CSRF token.
      const s = await api<{ csrf_token: string }>("/api/auth/password", {
        method: "POST",
        body: { current_password: current, new_password: next },
      });
      setCsrfToken(s.csrf_token);
      setCurrent("");
      setNext("");
      setRepeat("");
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change the password. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Account</h1>
      <p className="mt-1 text-sm text-dim">{user?.display_name} · {user?.email}</p>

      <form onSubmit={(e) => void submit(e)} className="glass mt-6 w-full max-w-md rounded-2xl p-6">
        <h2 className="font-semibold">Change password</h2>
        <p className="mt-1 text-sm text-dim">You stay signed in here. Every other device is signed out.</p>
        <Field className="mt-5" label="Current password" type="password" autoComplete="current-password" required
          value={current} onChange={(e) => setCurrent(e.target.value)} />
        <Field className="mt-4" label="New password" type="password" autoComplete="new-password" required
          minLength={MIN_PASSWORD_LENGTH} hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
          value={next} onChange={(e) => setNext(e.target.value)} />
        <Field className="mt-4" label="Repeat new password" type="password" autoComplete="new-password" required
          value={repeat} onChange={(e) => setRepeat(e.target.value)} />
        {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
        {done && <p role="status" className="mt-4 text-sm text-cyan">Password changed. Other devices were signed out.</p>}
        <button className="btn btn-primary mt-6 w-full" disabled={busy || !current || !next || !repeat}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          {busy ? "Saving" : "Change password"}
        </button>
      </form>
    </section>
  );
}

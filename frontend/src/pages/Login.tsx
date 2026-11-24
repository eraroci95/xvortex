import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Field } from "../components/ui/Field";
import { Vortex } from "../components/ui/Vortex";
import { ApiError } from "../lib/api";

export default function Login() {
  const { user, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={(location.state as { from?: string } | null)?.from ?? "/"} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-full max-w-6xl items-center gap-10 px-6 py-10 lg:grid-cols-2">
      <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
        <Vortex size={300} />
        <h1 className="mt-6 text-4xl font-semibold tracking-tight">XVORTEX</h1>
        <p className="mt-3 max-w-sm text-dim">Your loans, markets and simulated portfolio in one private workspace.</p>
      </div>

      <form onSubmit={onSubmit} className="glass mx-auto w-full max-w-md rounded-2xl p-7" noValidate>
        <h2 className="text-xl font-semibold">Sign in</h2>
        <p className="mt-1 text-sm text-dim">Accounts are created by the administrator.</p>
        <Field className="mt-6" label="Email" type="email" autoComplete="username" required
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field className="mt-4" label="Password" type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
        <button className="btn btn-primary mt-6 w-full" disabled={busy || !email || !password}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          {busy ? "Signing in" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import { useAuth, type User } from "../auth/AuthContext";

export default function Admin() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", display_name: "", password: "", is_admin: false });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<User[]>("/api/admin/users").then(setUsers).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/admin/users", { method: "POST", body: form });
      setForm({ email: "", display_name: "", password: "", is_admin: false });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the user.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(u: User) {
    setError(null);
    try {
      await api(`/api/admin/users/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the user.");
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Users</h1>
      {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_22rem]">
        <div className="glass overflow-x-auto rounded-2xl">
          <table className="w-full text-left text-sm">
            <thead className="text-dim">
              <tr><th className="p-4 font-medium">Name</th><th className="p-4 font-medium">Email</th>
                <th className="p-4 font-medium">Role</th><th className="p-4" /></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-white/5">
                  <td className="p-4">{u.display_name}</td>
                  <td className="p-4">{u.email}</td>
                  <td className="p-4">{u.is_admin ? "Administrator" : "Member"}{!u.is_active && " (inactive)"}</td>
                  <td className="p-4 text-right">
                    {u.id !== me?.id && (
                      <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => toggle(u)}>
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form onSubmit={create} className="glass h-fit rounded-2xl p-5">
          <h2 className="font-semibold">Add a user</h2>
          <Field className="mt-4" label="Name" required value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <Field className="mt-3" label="Email" type="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <Field className="mt-3" label="Password" type="password" required minLength={12} autoComplete="new-password"
            hint="At least 12 characters." value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_admin}
              onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} />
            Administrator
          </label>
          <button className="btn btn-primary mt-5 w-full" disabled={busy}>Create user</button>
        </form>
      </div>
    </section>
  );
}

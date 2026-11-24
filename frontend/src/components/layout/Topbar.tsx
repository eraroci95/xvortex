import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, LogOut, Menu, Moon, Search, Sun } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { useTheme } from "../../theme/ThemeContext";
import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { AppNotification } from "../../lib/types";
import { useApi } from "../../lib/useApi";
import { NAV_ITEMS } from "./nav";

function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return { open, setOpen, ref };
}

export function Topbar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const bell = usePopover();
  const notes = useApi<{ unread: number; items: AppNotification[] }>("/api/notifications?limit=10");
  const unread = notes.data?.unread ?? 0;

  function toggleBell() {
    if (!bell.open) notes.reload();
    bell.setOpen(!bell.open);
  }

  async function markAllRead() {
    await api("/api/notifications/read-all", { method: "POST" });
    notes.reload();
  }
  const profile = usePopover();

  const matches = query.trim()
    ? NAV_ITEMS.filter((i) => (!i.adminOnly || user?.is_admin) && i.label.toLowerCase().includes(query.trim().toLowerCase()))
    : [];

  function go(to: string) { setQuery(""); navigate(to); }

  return (
    <header className="glass relative z-20 flex h-16 items-center gap-3 px-4">
      <button className="rounded-lg p-2 hover:bg-white/10 lg:hidden" onClick={onOpenMenu} aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </button>

      <div className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" aria-hidden />
        <input className="field !py-2 !pl-9" type="search" placeholder="Search pages" aria-label="Search pages"
          value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && matches[0]) go(matches[0].to); if (e.key === "Escape") setQuery(""); }} />
        {query.trim() && (
          <ul className="glass absolute left-0 right-0 top-full mt-2 rounded-xl p-1">
            {matches.length === 0 && <li className="px-3 py-2 text-sm text-dim">No matching pages.</li>}
            {matches.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-white/10" onClick={() => go(to)}>
                  <Icon className="h-4 w-4 text-dim" aria-hidden />{label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1">
        <button className="rounded-lg p-2 hover:bg-white/10" onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        <div className="relative" ref={bell.ref}>
          <button className="relative rounded-lg p-2 hover:bg-white/10" onClick={toggleBell}
            aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"} aria-expanded={bell.open}>
            <Bell className="h-5 w-5" />
            {unread > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-cyan" aria-hidden />}
          </button>
          {bell.open && (
            <div className="glass absolute right-0 top-full mt-2 w-80 rounded-xl p-4 text-sm">
              <div className="flex items-center justify-between">
                <p className="font-medium">Notifications</p>
                {unread > 0 && (
                  <button className="text-xs text-cyan hover:underline" onClick={() => void markAllRead()}>Mark all read</button>
                )}
              </div>
              {notes.error && <p className="mt-2 text-danger">{notes.error}</p>}
              {!notes.error && (notes.data?.items.length ?? 0) === 0 && (
                <p className="mt-2 text-dim">You're all caught up. Alerts about overdue loans and other changes will show here.</p>
              )}
              <ul className="mt-2 max-h-72 divide-y divide-white/5 overflow-y-auto">
                {notes.data?.items.map((n) => (
                  <li key={n.id} className="py-2">
                    <p className={n.read ? "text-dim" : "font-medium"}>{n.title}</p>
                    {n.body && <p className="text-dim">{n.body}</p>}
                    <p className="mt-0.5 text-xs text-dim">{formatDateTime(n.created_at)}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="relative" ref={profile.ref}>
          <button className="ml-1 flex items-center gap-2 rounded-xl p-1.5 hover:bg-white/10"
            onClick={() => profile.setOpen(!profile.open)} aria-label="Account menu" aria-expanded={profile.open}>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-cyan to-violet text-sm font-semibold text-[rgb(5,11,26)]">
              {(user?.display_name ?? "?").charAt(0).toUpperCase()}
            </span>
          </button>
          {profile.open && (
            <div className="glass absolute right-0 top-full mt-2 w-64 rounded-xl p-2 text-sm">
              <div className="px-3 py-2">
                <p className="font-medium">{user?.display_name}</p>
                <p className="truncate text-dim">{user?.email}</p>
              </div>
              <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 hover:bg-white/10" onClick={() => void logout()}>
                <LogOut className="h-4 w-4" aria-hidden />Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

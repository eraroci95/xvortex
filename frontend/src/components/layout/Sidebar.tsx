import { NavLink } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { NAV_ITEMS } from "./nav";

interface Props {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onNavigate?: () => void;
  mobile?: boolean;
}

export function Sidebar({ collapsed, onToggleCollapsed, onNavigate, mobile = false }: Props) {
  const { user } = useAuth();
  const narrow = collapsed && !mobile;

  return (
    <nav aria-label="Main" className={`glass flex h-full flex-col ${narrow ? "w-[4.5rem]" : "w-64"} transition-[width] duration-200`}>
      <div className="flex h-16 items-center justify-between px-4">
        <span className={`text-lg font-semibold tracking-tight ${narrow ? "sr-only" : ""}`}>XVORTEX</span>
        {mobile ? (
          <button className="rounded-lg p-2 hover:bg-white/10" onClick={onNavigate} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        ) : (
          <button className="rounded-lg p-2 hover:bg-white/10" onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
          </button>
        )}
      </div>
      <ul className="flex-1 space-y-1 px-2 py-2">
        {NAV_ITEMS.filter((i) => !i.adminOnly || user?.is_admin).map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink to={to} end={to === "/"} onClick={onNavigate} title={narrow ? label : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive ? "bg-cyan/15 text-cyan" : "text-dim hover:bg-white/5 hover:text-fg"
                }`}>
              <Icon className="h-5 w-5 shrink-0" aria-hidden />
              <span className={narrow ? "sr-only" : ""}>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

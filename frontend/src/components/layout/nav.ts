import { BarChart3, Landmark, LayoutDashboard, LineChart, ShieldCheck, Sparkles, Wallet, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Command Center", icon: LayoutDashboard },
  { to: "/loans", label: "Loans", icon: Landmark },
  { to: "/market", label: "Market", icon: LineChart },
  { to: "/paper", label: "Paper Trading", icon: Wallet },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/assistant", label: "Assistant", icon: Sparkles },
  { to: "/admin", label: "Users", icon: ShieldCheck, adminOnly: true },
];

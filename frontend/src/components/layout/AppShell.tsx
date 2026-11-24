import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

function initialCollapsed(): boolean {
  try { return localStorage.getItem("xv-sidebar") === "collapsed"; } catch { return false; }
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [drawer, setDrawer] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => {
    try { localStorage.setItem("xv-sidebar", collapsed ? "collapsed" : "expanded"); } catch { /* ignore */ }
  }, [collapsed]);

  return (
    <div className="flex h-full gap-3 p-3">
      <div className="hidden lg:block">
        <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((c) => !c)} />
      </div>

      <AnimatePresence>
        {drawer && (
          <>
            <motion.div className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setDrawer(false)}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.div className="fixed inset-y-3 left-3 z-40 lg:hidden"
              initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }} transition={{ type: "tween", duration: 0.2 }}>
              <Sidebar mobile collapsed={false} onToggleCollapsed={() => undefined} onNavigate={() => setDrawer(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <Topbar onOpenMenu={() => setDrawer(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto rounded-2xl p-1 sm:p-3">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

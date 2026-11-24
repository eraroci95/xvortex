import { useEffect, useState } from "react";
import { Loader2, RefreshCw, SlidersHorizontal } from "lucide-react";
import { CustomizePanel } from "../components/dashboard/CustomizePanel";
import { WIDGETS } from "../components/widgets/registry";
import { api, ApiError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { DashboardSummary, WidgetPref } from "../lib/types";
import { useApi } from "../lib/useApi";

export default function CommandCenter() {
  const summary = useApi<DashboardSummary>("/api/dashboard/summary");
  const layout = useApi<{ widgets: WidgetPref[] }>("/api/settings/dashboard-layout");
  const [editing, setEditing] = useState(false);
  const [widgets, setWidgets] = useState<WidgetPref[] | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => { if (layout.data) setWidgets(layout.data.widgets); }, [layout.data]);

  async function finishEditing() {
    if (!widgets) return;
    setSaveError(null);
    try {
      await api("/api/settings/dashboard-layout", { method: "PUT", body: { widgets } });
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save the layout. Try again.");
    }
  }

  const error = summary.error ?? layout.error;
  if (error && !summary.data) {
    return (
      <div role="alert" className="glass max-w-lg rounded-2xl p-6">
        <p className="font-medium">The dashboard could not load.</p>
        <p className="mt-1 text-sm text-dim">{error}</p>
        <button className="btn btn-ghost mt-4" onClick={() => { summary.reload(); layout.reload(); }}>Try again</button>
      </div>
    );
  }
  if (!summary.data || !widgets) {
    return (
      <div className="flex justify-center py-20" role="status" aria-label="Loading dashboard">
        <Loader2 className="h-6 w-6 animate-spin text-cyan" />
      </div>
    );
  }

  return (
    <section>
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Command Center</h1>
          <p className="mt-1 text-sm text-dim">Calculated from your records at {formatDateTime(summary.data.generated_at)}.</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-ghost" onClick={summary.reload} disabled={summary.loading}>
            <RefreshCw className={`h-4 w-4 ${summary.loading ? "animate-spin" : ""}`} aria-hidden />Refresh
          </button>
          {editing ? (
            <button className="btn btn-primary" onClick={() => void finishEditing()}>Save layout</button>
          ) : (
            <button className="btn btn-ghost" onClick={() => setEditing(true)}>
              <SlidersHorizontal className="h-4 w-4" aria-hidden />Customize
            </button>
          )}
        </div>
      </header>

      {saveError && <p role="alert" className="mb-3 text-sm text-danger">{saveError}</p>}
      {editing && <CustomizePanel widgets={widgets} onChange={setWidgets} />}

      <div className="grid gap-4 xl:grid-cols-2">
        {widgets.filter((w) => w.visible).map((w) => {
          const { Component } = WIDGETS[w.id];
          return <Component key={w.id} data={summary.data!} />;
        })}
      </div>
      {widgets.every((w) => !w.visible) && (
        <p className="text-sm text-dim">All widgets are hidden. Choose Customize to show some.</p>
      )}
    </section>
  );
}

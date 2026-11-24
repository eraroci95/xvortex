import { formatDateTime } from "../../lib/format";
import type { DashboardSummary } from "../../lib/types";
import { Empty, WidgetFrame } from "./WidgetFrame";

export function AlertsWidget({ data }: { data: DashboardSummary }) {
  const { unread, latest } = data.notifications;
  return (
    <WidgetFrame title="Alerts" aside={unread > 0 ? <span className="num text-sm text-cyan">{unread} unread</span> : undefined}>
      {latest.length === 0 ? (
        <Empty>You're all caught up. Overdue loans and other alerts will show here.</Empty>
      ) : (
        <ul className="divide-y divide-white/5">
          {latest.map((n) => (
            <li key={n.id} className="py-2 text-sm">
              <p className={n.read ? "text-dim" : "font-medium"}>{n.title}</p>
              {n.body && <p className="text-dim">{n.body}</p>}
              <p className="mt-0.5 text-xs text-dim">{formatDateTime(n.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </WidgetFrame>
  );
}

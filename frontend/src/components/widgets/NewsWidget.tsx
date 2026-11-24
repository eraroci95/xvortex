import type { DashboardSummary } from "../../lib/types";
import { Unavailable, WidgetFrame } from "./WidgetFrame";

export function NewsWidget({ data }: { data: DashboardSummary }) {
  return (
    <WidgetFrame title="Financial news">
      {data.news.status === "unavailable" ? (
        <Unavailable>No news source is connected yet. Headlines will appear here once one is.</Unavailable>
      ) : (
        <p className="text-sm text-dim">No headlines right now.</p>
      )}
    </WidgetFrame>
  );
}

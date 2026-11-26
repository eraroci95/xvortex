import { formatDate, formatMoney } from "../../lib/format";
import type { InstallmentRow } from "../../lib/types";
import { InstallmentBadge } from "./labels";

export function ScheduleTable({ rows, currency, showProgress }: { rows: InstallmentRow[]; currency: string; showProgress: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-dim">
          <tr>
            <th className="py-2 pr-3 font-medium">#</th>
            <th className="py-2 pr-3 font-medium">Due</th>
            <th className="py-2 pr-3 text-right font-medium">Principal</th>
            <th className="py-2 pr-3 text-right font-medium">Interest</th>
            <th className="py-2 pr-3 text-right font-medium">Total</th>
            {showProgress && <th className="py-2 pr-3 text-right font-medium">Still owed</th>}
            {showProgress && <th className="py-2 font-medium">Status</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.number} className="border-t border-line/15">
              <td className="py-2 pr-3 num">{r.number}</td>
              <td className="py-2 pr-3">{formatDate(r.due_date, "UTC")}</td>
              <td className="py-2 pr-3 text-right num">{formatMoney(r.principal, currency)}</td>
              <td className="py-2 pr-3 text-right num">{formatMoney(r.interest, currency)}</td>
              <td className="py-2 pr-3 text-right num">{formatMoney(r.total, currency)}</td>
              {showProgress && <td className="py-2 pr-3 text-right num">{formatMoney(r.outstanding, currency)}</td>}
              {showProgress && <td className="py-2"><InstallmentBadge status={r.status} /></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

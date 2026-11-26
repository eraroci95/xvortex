import type { Frequency, InstallmentStatus, LoanStatus, Method, Risk } from "../../lib/types";

export const FREQUENCY_LABEL: Record<Frequency, string> = {
  weekly: "Weekly", biweekly: "Every 2 weeks", monthly: "Monthly",
  quarterly: "Quarterly", semiannual: "Every 6 months", annual: "Yearly",
};

export const METHOD_LABEL: Record<Method, string> = {
  annuity: "Equal installments (annuity)",
  equal_principal: "Equal principal",
  interest_only: "Interest only, principal at the end",
};

const STATUS_LABEL: Record<LoanStatus, string> = { active: "Active", repaid: "Repaid", closed: "Closed" };

// Colour is never the only signal: each badge also carries its text.
const TONE = {
  good: "border-cyan/40 text-cyan",
  warn: "border-amber-500/50 text-amber-500",
  bad: "border-danger/50 text-danger",
  muted: "border-line/30 text-dim",
} as const;

function Badge({ tone, children }: { tone: keyof typeof TONE; children: string }) {
  return <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}>{children}</span>;
}

export function StatusBadge({ status, archived }: { status: LoanStatus; archived?: boolean }) {
  if (archived) return <Badge tone="muted">Archived</Badge>;
  return <Badge tone={status === "active" ? "good" : "muted"}>{STATUS_LABEL[status]}</Badge>;
}

export function RiskBadge({ risk }: { risk: Risk | null }) {
  if (!risk) return <span className="text-dim">—</span>;
  const tone = risk.level === "high" ? "bad" : risk.level === "medium" ? "warn" : "good";
  return <Badge tone={tone}>{`${risk.level[0].toUpperCase()}${risk.level.slice(1)} risk`}</Badge>;
}

const INSTALLMENT_LABEL: Record<InstallmentStatus, string> = {
  paid: "Paid", partial: "Part paid", overdue: "Overdue", upcoming: "Upcoming",
};

export function InstallmentBadge({ status }: { status: InstallmentStatus }) {
  const tone = status === "paid" ? "good" : status === "overdue" ? "bad" : status === "partial" ? "warn" : "muted";
  return <Badge tone={tone}>{INSTALLMENT_LABEL[status]}</Badge>;
}

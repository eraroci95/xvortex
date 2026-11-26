export type WidgetId = "loans" | "paper" | "market" | "transactions" | "news" | "alerts";

export interface WidgetPref { id: WidgetId; visible: boolean }

export interface LoanTotals {
  currency: string;
  active_loans: number;
  overdue_loans: number;
  total_lent: string;
  outstanding_principal: string;
  remaining_interest: string;
  overdue_amount: string;
  unapplied_payments: string;
}

export interface PaperSummary {
  accounts: number;
  currency: string;
  cash: string;
  starting_cash: string;
  invested_at_cost: string;
  realized_pnl: string;
  market_value: string | null;
  unrealized_pnl: string | null;
  valuation_status: string;
}

export interface WatchlistBrief { id: string; name: string; symbol_count: number; symbols: string[] }

export interface Transaction {
  kind: "paper_trade" | "loan_payment";
  label: string;
  amount: string;
  currency: string | null;
  occurred_at: string;
  simulated: boolean;
}

export interface AppNotification {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  created_at: string;
  read: boolean;
}

export interface DashboardSummary {
  generated_at: string;
  loans: LoanTotals[];
  paper: PaperSummary;
  watchlists: WatchlistBrief[];
  market_data_status: string;
  transactions: Transaction[];
  news: { status: string; items: unknown[] };
  notifications: { unread: number; latest: AppNotification[] };
}

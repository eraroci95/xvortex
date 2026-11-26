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
  excluded_accounts: number;
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

// ---- Loans (phase 4). Amounts are decimal strings; dates are YYYY-MM-DD. ----
export type Frequency = "weekly" | "biweekly" | "monthly" | "quarterly" | "semiannual" | "annual";
export type Method = "annuity" | "equal_principal" | "interest_only";
export type LoanStatus = "active" | "repaid" | "closed";
export type InstallmentStatus = "paid" | "partial" | "overdue" | "upcoming";

export interface Borrower {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
  archived: boolean;
  loan_count: number;
  active_loan_count: number;
  created_at: string;
}

export interface Risk { level: "low" | "medium" | "high"; triggers: string[]; disclaimer: string }

export interface InstallmentRow {
  number: number;
  due_date: string;
  principal: string;
  interest: string;
  total: string;
  paid_principal: string;
  paid_interest: string;
  outstanding: string;
  status: InstallmentStatus;
}

export interface LoanSummary {
  id: string;
  borrower_id: string;
  borrower_name: string;
  principal: string;
  annual_interest_rate: string;
  currency: string;
  start_date: string;
  maturity_date: string;
  repayment_frequency: Frequency;
  amortization_method: Method;
  status: LoanStatus;
  archived: boolean;
  outstanding_principal: string;
  remaining_interest: string;
  overdue_amount: string;
  overdue_installments: number;
  unapplied_payments: string;
  next_due_date: string | null;
  next_due_amount: string | null;
  risk: Risk | null;
}

export interface LoanPaymentRow { id: string; paid_on: string; amount: string; note: string | null }

export interface LoanDetail extends LoanSummary {
  notes: string | null;
  created_at: string;
  total_paid: string;
  schedule: InstallmentRow[];
  payments: LoanPaymentRow[];
}

export interface LoanPreview {
  installments: InstallmentRow[];
  total_principal: string;
  total_interest: string;
  total_repayable: string;
}

// ---- Market (phase 5). Prices are end-of-day. ----
export interface Instrument {
  symbol: string;
  name: string | null;
  last_close: string | null;
  change_pct: string | null;
  as_of: string | null;
  fetched_at: string | null;
}
export interface Watchlist { id: string; name: string; instruments: Instrument[] }
export interface MarketStatus { configured: boolean; budget_used: number; budget_limit: number }
export interface DailyBar { date: string; open: string; high: string; low: string; close: string; volume: number }
export interface DailyPrices {
  symbol: string;
  bars: DailyBar[];
  sma20: (string | null)[];
  sma50: (string | null)[];
  rsi14: (string | null)[];
  fetched_at: string;
  expires_at: string;
  stale: boolean;
  warning: string | null;
  source: string;
  note: string;
}

// ---- Paper trading (phase 6). Everything here is simulated. ----
export interface PaperPosition {
  symbol: string;
  quantity: string;
  avg_entry_price: string;
  cost_basis: string;
  last_close: string | null;
  price_date: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  realized_pnl: string;
}
export interface PaperTrade {
  id: string;
  executed_at: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: string;
  price: string;
  amount: string;
  fees: string;
  realized_pnl: string | null;
  simulated: boolean;
}
export interface PaperAccount {
  id: string;
  name: string;
  currency: string;
  starting_cash: string;
  cash_balance: string;
  positions: PaperPosition[];
  market_value: string | null;
  equity: string | null;
  unrealized_pnl: string | null;
  realized_pnl: string;
  valuation_status: "end_of_day" | "partial" | "unavailable";
  trades: PaperTrade[];
  simulated: boolean;
}
export interface OrderResult { account: PaperAccount; trade: PaperTrade; price_date: string }

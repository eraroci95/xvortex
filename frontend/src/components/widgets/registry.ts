import type { ComponentType } from "react";
import type { DashboardSummary, WidgetId } from "../../lib/types";
import { AlertsWidget } from "./AlertsWidget";
import { LoansWidget } from "./LoansWidget";
import { MarketWidget } from "./MarketWidget";
import { NewsWidget } from "./NewsWidget";
import { PaperWidget } from "./PaperWidget";
import { TransactionsWidget } from "./TransactionsWidget";

export const WIDGETS: Record<WidgetId, { title: string; Component: ComponentType<{ data: DashboardSummary }> }> = {
  loans: { title: "Loans", Component: LoansWidget },
  paper: { title: "Paper trading", Component: PaperWidget },
  market: { title: "Market watch", Component: MarketWidget },
  transactions: { title: "Recent transactions", Component: TransactionsWidget },
  news: { title: "Financial news", Component: NewsWidget },
  alerts: { title: "Alerts", Component: AlertsWidget },
};

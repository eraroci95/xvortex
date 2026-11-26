import { useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import { formatDate, formatDateTime, formatMoney, isNegative } from "../lib/format";
import type { OrderResult, PaperAccount, Watchlist } from "../lib/types";
import { useApi } from "../lib/useApi";

const message = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Try again.");

function Pnl({ value, currency }: { value: string | null; currency: string }) {
  if (value === null) return <span className="text-dim">—</span>;
  const n = Number(value);
  return <span className={`num ${isNegative(value) ? "text-danger" : n > 0 ? "text-cyan" : ""}`}>{n > 0 ? "+" : ""}{formatMoney(value, currency)}</span>;
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-line/15 p-3">
      <p className="text-xs uppercase tracking-wide text-dim">{label}</p>
      <p className="mt-1 text-lg num">{children}</p>
    </div>
  );
}

function OrderForm({ account, symbols, onDone }: { account: PaperAccount; symbols: string[]; onDone: (r: OrderResult) => void }) {
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listId = `symbols-${account.id}`;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!window.confirm(`Simulated ${side}: ${quantity} ${sym} at the latest saved close. No real order is sent. Continue?`)) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api<OrderResult>(`/api/paper/accounts/${account.id}/orders`, { method: "POST", body: { symbol: sym, side, quantity } });
      setQuantity("");
      onDone(result);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="mt-4 grid items-end gap-4 sm:grid-cols-4">
      <div>
        <Field label="Symbol" required maxLength={16} list={listId} value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
        <datalist id={listId}>{symbols.map((s) => <option key={s} value={s} />)}</datalist>
      </div>
      <div>
        <label htmlFor={`side-${account.id}`} className="mb-1.5 block text-sm font-medium">Side</label>
        <select id={`side-${account.id}`} className="field" value={side} onChange={(e) => setSide(e.target.value as "buy" | "sell")}>
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>
      </div>
      <Field label="Quantity" required inputMode="decimal" pattern="[0-9]+([.][0-9]{1,4})?" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
      <button className="btn btn-primary" disabled={busy || !symbol.trim() || !quantity}>
        {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}Place simulated order
      </button>
      {error && <p role="alert" className="text-sm text-danger sm:col-span-4">{error}</p>}
    </form>
  );
}

function Account({ account, symbols, onChange, onDeleted }: {
  account: PaperAccount; symbols: string[]; onChange: (a: PaperAccount) => void; onDeleted: () => void;
}) {
  const cur = account.currency;
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    if (!window.confirm(`Delete "${account.name}" with all its positions and trades? This cannot be undone.`)) return;
    try { await api(`/api/paper/accounts/${account.id}`, { method: "DELETE" }); onDeleted(); } catch (err) { setError(message(err)); }
  }

  return (
    <div className="glass mt-6 rounded-2xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{account.name} <span className="text-sm font-normal text-dim">{cur}</span></h2>
        <span className="rounded-full border border-violet/40 px-2 py-0.5 text-xs text-violet">Simulated</span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Cash">{formatMoney(account.cash_balance, cur)}</Stat>
        <Stat label="Total value">{account.equity !== null ? formatMoney(account.equity, cur) : <span className="text-dim">needs prices</span>}</Stat>
        <Stat label="Unrealized"><Pnl value={account.unrealized_pnl} currency={cur} /></Stat>
        <Stat label="Realized"><Pnl value={account.realized_pnl} currency={cur} /></Stat>
      </div>
      {account.valuation_status !== "end_of_day" && (
        <p className="mt-3 text-sm text-amber-500">
          Some positions have no saved price, so totals are not shown. Load them in <Link to="/market" className="underline">Market</Link>.
        </p>
      )}

      <OrderForm account={account} symbols={symbols} onDone={(r) => {
        onChange(r.account);
        setNote(`${r.trade.side === "buy" ? "Bought" : "Sold"} ${Number(r.trade.quantity)} ${r.trade.symbol} at ${r.trade.price}, the close of ${formatDate(r.price_date, "UTC")}. Simulated.`);
      }} />
      {note && <p role="status" className="mt-3 text-sm text-cyan">{note}</p>}
      <p className="mt-2 text-xs text-dim">
        Orders are simulated market orders filled at the latest saved end-of-day close, with no fees. Only symbols on a
        watchlist can be traded, and you cannot spend more cash than you have or sell more than you hold. Cash and prices are
        taken to be in {cur}; nothing is converted.
      </p>

      <h3 className="mt-6 font-semibold">Positions</h3>
      {account.positions.length === 0 ? <p className="mt-2 text-sm text-dim">No open positions.</p> : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-dim">
              <tr><th className="py-2 pr-3 font-medium">Symbol</th><th className="py-2 pr-3 text-right font-medium">Quantity</th>
                <th className="py-2 pr-3 text-right font-medium">Avg entry</th><th className="py-2 pr-3 text-right font-medium">Last close</th>
                <th className="py-2 pr-3 text-right font-medium">Value</th><th className="py-2 text-right font-medium">Unrealized</th></tr>
            </thead>
            <tbody>
              {account.positions.map((p) => (
                <tr key={p.symbol} className="border-t border-line/15">
                  <td className="py-2 pr-3 font-medium">{p.symbol}</td>
                  <td className="py-2 pr-3 text-right num">{Number(p.quantity)}</td>
                  <td className="py-2 pr-3 text-right num">{Number(p.avg_entry_price)}</td>
                  <td className="py-2 pr-3 text-right num">
                    {p.last_close ?? <span className="text-dim">no price</span>}
                    {p.price_date && <div className="text-xs text-dim">{formatDate(p.price_date, "UTC")}</div>}
                  </td>
                  <td className="py-2 pr-3 text-right num">{p.market_value ? formatMoney(p.market_value, cur) : "—"}</td>
                  <td className="py-2 text-right"><Pnl value={p.unrealized_pnl} currency={cur} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mt-6 font-semibold">Recent trades</h3>
      {account.trades.length === 0 ? <p className="mt-2 text-sm text-dim">No trades yet.</p> : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-dim">
              <tr><th className="py-2 pr-3 font-medium">When</th><th className="py-2 pr-3 font-medium">Trade</th>
                <th className="py-2 pr-3 text-right font-medium">Price</th><th className="py-2 pr-3 text-right font-medium">Amount</th>
                <th className="py-2 text-right font-medium">Realized</th></tr>
            </thead>
            <tbody>
              {account.trades.map((t) => (
                <tr key={t.id} className="border-t border-line/15">
                  <td className="py-2 pr-3 text-dim">{formatDateTime(t.executed_at)}</td>
                  <td className="py-2 pr-3">{t.side === "buy" ? "Bought" : "Sold"} <span className="num">{Number(t.quantity)}</span> {t.symbol}</td>
                  <td className="py-2 pr-3 text-right num">{Number(t.price)}</td>
                  <td className="py-2 pr-3 text-right num">{formatMoney(t.amount, cur)}</td>
                  <td className="py-2 text-right">{t.side === "sell" ? <Pnl value={t.realized_pnl} currency={cur} /> : <span className="text-dim">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
      <div className="mt-6"><button className="btn btn-ghost" onClick={() => void remove()}>Delete account</button></div>
    </div>
  );
}

export default function Paper() {
  const { data: accounts, error, loading, reload } = useApi<PaperAccount[]>("/api/paper/accounts");
  const { data: lists } = useApi<Watchlist[]>("/api/market/watchlists");
  const [replaced, setReplaced] = useState<Record<string, PaperAccount>>({});
  const [name, setName] = useState("");
  const [cash, setCash] = useState("10000");
  const [currency, setCurrency] = useState("SEK");
  const [busy, setBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const symbols = [...new Set((lists ?? []).flatMap((w) => w.instruments.map((i) => i.symbol)))].sort();

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setCreateError(null);
    try {
      await api("/api/paper/accounts", { method: "POST", body: { name, starting_cash: cash, currency } });
      setName("");
      reload();
    } catch (err) {
      setCreateError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Paper trading</h1>
      <p className="mt-1 text-sm text-dim">Practise with virtual cash. Everything here is simulated: no real order is ever placed and no real money moves.</p>

      <form onSubmit={(e) => void create(e)} className="glass mt-6 grid items-end gap-4 rounded-2xl p-5 sm:grid-cols-4">
        <Field label="New account" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Virtual starting cash" required inputMode="decimal" pattern="[0-9]+([.][0-9]{1,2})?" value={cash} onChange={(e) => setCash(e.target.value)} />
        <Field label="Currency" required maxLength={3} minLength={3} pattern="[A-Za-z]{3}" value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
        <button className="btn btn-primary" disabled={busy || !name.trim() || !cash}>Create account</button>
        {createError && <p role="alert" className="text-sm text-danger sm:col-span-4">{createError}</p>}
      </form>

      {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
      {loading && !accounts && <p className="mt-4 text-sm text-dim" role="status">Loading…</p>}
      {accounts && accounts.length === 0 && <p className="mt-4 text-sm text-dim">No accounts yet.</p>}
      {symbols.length === 0 && accounts && accounts.length > 0 && (
        <p className="mt-4 text-sm text-dim">Add symbols to a watchlist in <Link to="/market" className="text-cyan underline">Market</Link> to trade them.</p>
      )}

      {accounts?.map((a) => (
        <Account key={a.id} account={replaced[a.id] ?? a} symbols={symbols}
          onChange={(next) => setReplaced((r) => ({ ...r, [a.id]: next }))}
          onDeleted={() => { setReplaced({}); reload(); }} />
      ))}
    </section>
  );
}

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Loader2, RefreshCw, Trash2 } from "lucide-react";
import { PriceChart } from "../components/market/PriceChart";
import { Field } from "../components/ui/Field";
import { api, ApiError } from "../lib/api";
import { formatDate, formatDateTime } from "../lib/format";
import type { DailyPrices, MarketStatus, Watchlist } from "../lib/types";
import { useApi } from "../lib/useApi";

const message = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Try again.");

function Change({ pct }: { pct: string | null }) {
  if (pct === null) return <span className="text-dim">—</span>;
  const n = Number(pct);
  // The sign and the arrow carry the direction, not only the colour.
  return <span className={`num ${n < 0 ? "text-danger" : n > 0 ? "text-cyan" : "text-dim"}`}>{n > 0 ? "▲ +" : n < 0 ? "▼ " : ""}{pct}%</span>;
}

function Prices({ symbol, onSettled }: { symbol: string; onSettled: () => void }) {
  const [data, setData] = useState<DailyPrices | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (refresh: boolean) => {
    setBusy(true);
    setError(null);
    try {
      setData(await api<DailyPrices>(`/api/market/symbols/${encodeURIComponent(symbol)}/daily${refresh ? "?refresh=true" : ""}`));
      onSettled();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }, [symbol, onSettled]);

  useEffect(() => { setData(null); void load(false); }, [load]);

  return (
    <div className="glass mt-6 rounded-2xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{symbol}</h2>
        <button className="btn btn-ghost" disabled={busy} onClick={() => void load(true)}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}Refresh prices
        </button>
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      {busy && !data && <p className="mt-3 text-sm text-dim" role="status">Loading prices…</p>}
      {data && (
        <>
          <p className="mt-2 text-xs text-dim">
            {data.source} · latest close {formatDate(data.bars[data.bars.length - 1].date, "UTC")} · saved {formatDateTime(data.fetched_at)}
            {data.stale ? " · out of date" : ""}
          </p>
          {data.warning && <p role="status" className="mt-2 text-sm text-amber-500">{data.warning}</p>}
          <div className="mt-4"><PriceChart data={data} /></div>
          <p className="mt-3 text-xs text-dim">{data.note}</p>
        </>
      )}
    </div>
  );
}

export default function Market() {
  const { data: lists, error, loading, reload } = useApi<Watchlist[]>("/api/market/watchlists");
  const { data: status, reload: reloadStatus } = useApi<MarketStatus>("/api/market/status");
  const [selected, setSelected] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [symbolInputs, setSymbolInputs] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function act(fn: () => Promise<unknown>): Promise<boolean> {
    setBusy(true);
    setActionError(null);
    try { await fn(); reload(); return true; } catch (err) { setActionError(message(err)); return false; } finally { setBusy(false); }
  }

  async function createList(e: FormEvent) {
    e.preventDefault();
    if (await act(() => api("/api/market/watchlists", { method: "POST", body: { name: newName } }))) setNewName("");
  }

  async function addSymbol(e: FormEvent, id: string) {
    e.preventDefault();
    const symbol = (symbolInputs[id] ?? "").trim();
    if (await act(() => api(`/api/market/watchlists/${id}/instruments`, { method: "POST", body: { symbol } }))) {
      setSymbolInputs((s) => ({ ...s, [id]: "" }));
    }
  }

  const onSettled = useCallback(() => { reload(); reloadStatus(); }, [reload, reloadStatus]);

  return (
    <section>
      <h1 className="text-2xl font-semibold">Market</h1>
      <p className="mt-1 text-sm text-dim">
        {status?.configured
          ? `End-of-day prices from Alpha Vantage, saved and reused for hours. Price requests today: ${status.budget_used} of ${status.budget_limit}.`
          : "No price provider key is configured, so watchlists work but prices are unavailable. Nothing is estimated."}
      </p>

      <form onSubmit={(e) => void createList(e)} className="glass mt-6 flex flex-wrap items-end gap-3 rounded-2xl p-5">
        <Field className="min-w-60 flex-1" label="New watchlist" required maxLength={100} value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button className="btn btn-primary" disabled={busy || !newName.trim()}>Create</button>
      </form>

      {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
      {actionError && <p role="alert" className="mt-4 text-sm text-danger">{actionError}</p>}
      {loading && !lists && <p className="mt-4 text-sm text-dim" role="status">Loading…</p>}
      {lists && lists.length === 0 && <p className="mt-4 text-sm text-dim">No watchlists yet.</p>}

      {lists?.map((w) => (
        <div key={w.id} className="glass mt-6 rounded-2xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-semibold">{w.name}</h2>
            <div className="flex gap-2">
              <button className="btn btn-ghost" disabled={busy} onClick={() => {
                const name = window.prompt("Rename watchlist", w.name);
                if (name && name.trim() && name !== w.name) void act(() => api(`/api/market/watchlists/${w.id}`, { method: "PATCH", body: { name } }));
              }}>Rename</button>
              <button className="btn btn-ghost" disabled={busy} onClick={() => {
                if (window.confirm(`Delete the watchlist "${w.name}"?`)) void act(async () => {
                  await api(`/api/market/watchlists/${w.id}`, { method: "DELETE" });
                  if (w.instruments.some((i) => i.symbol === selected)) setSelected(null);
                });
              }}>Delete</button>
            </div>
          </div>

          {w.instruments.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[30rem] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-dim">
                  <tr><th className="py-2 pr-3 font-medium">Symbol</th><th className="py-2 pr-3 text-right font-medium">Last close</th>
                    <th className="py-2 pr-3 text-right font-medium">Change</th><th className="py-2 pr-3 font-medium">As of</th><th /></tr>
                </thead>
                <tbody>
                  {w.instruments.map((i) => (
                    <tr key={i.symbol} className="border-t border-line/15">
                      <td className="py-2 pr-3">
                        <button className={`font-medium hover:underline ${selected === i.symbol ? "text-fg" : "text-cyan"}`}
                          aria-pressed={selected === i.symbol} onClick={() => setSelected(i.symbol)}>{i.symbol}</button>
                        {i.name && <div className="text-xs text-dim">{i.name}</div>}
                      </td>
                      <td className="py-2 pr-3 text-right num">{i.last_close ?? <span className="text-dim">not loaded</span>}</td>
                      <td className="py-2 pr-3 text-right"><Change pct={i.change_pct} /></td>
                      <td className="py-2 pr-3 text-dim">{i.as_of ? formatDate(i.as_of, "UTC") : "—"}</td>
                      <td className="py-2 text-right">
                        <button className="text-dim hover:text-danger" aria-label={`Remove ${i.symbol} from ${w.name}`} disabled={busy}
                          onClick={() => void act(async () => {
                            await api(`/api/market/watchlists/${w.id}/instruments/${encodeURIComponent(i.symbol)}`, { method: "DELETE" });
                            if (selected === i.symbol) setSelected(null);
                          })}><Trash2 className="h-4 w-4" aria-hidden /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <form onSubmit={(e) => void addSymbol(e, w.id)} className="mt-4 flex flex-wrap items-end gap-3">
            <Field className="w-48" label="Add symbol" maxLength={16} placeholder="IBM" hint="As the provider spells it, for example VOLV-B.STO"
              value={symbolInputs[w.id] ?? ""} onChange={(e) => setSymbolInputs((s) => ({ ...s, [w.id]: e.target.value.toUpperCase() }))} />
            <button className="btn btn-ghost" disabled={busy || !(symbolInputs[w.id] ?? "").trim()}>Add</button>
          </form>
        </div>
      ))}

      {selected && <Prices key={selected} symbol={selected} onSettled={onSettled} />}
      {lists && lists.length > 0 && !selected && <p className="mt-6 text-sm text-dim">Choose a symbol to load its daily prices and chart.</p>}
    </section>
  );
}

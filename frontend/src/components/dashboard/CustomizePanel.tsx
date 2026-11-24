import { ArrowDown, ArrowUp, GripVertical } from "lucide-react";
import { Reorder, useDragControls } from "framer-motion";
import type { WidgetPref } from "../../lib/types";
import { WIDGETS } from "../widgets/registry";

interface Props {
  widgets: WidgetPref[];
  onChange: (next: WidgetPref[]) => void;
}

function Item({ w, index, total, onToggle, onMove }: {
  w: WidgetPref; index: number; total: number; onToggle: () => void; onMove: (dir: -1 | 1) => void;
}) {
  const controls = useDragControls();
  const title = WIDGETS[w.id].title;
  return (
    <Reorder.Item value={w} dragListener={false} dragControls={controls}
      className="glass flex items-center gap-3 rounded-xl px-3 py-2">
      <button className="cursor-grab touch-none rounded p-1 text-dim hover:text-fg" aria-label={`Drag ${title}`}
        onPointerDown={(e) => controls.start(e)}>
        <GripVertical className="h-5 w-5" aria-hidden />
      </button>
      <label className="flex flex-1 items-center gap-2 text-sm">
        <input type="checkbox" checked={w.visible} onChange={onToggle} />
        {title}
      </label>
      <button className="rounded p-1 hover:bg-white/10 disabled:opacity-30" disabled={index === 0}
        onClick={() => onMove(-1)} aria-label={`Move ${title} up`}><ArrowUp className="h-4 w-4" /></button>
      <button className="rounded p-1 hover:bg-white/10 disabled:opacity-30" disabled={index === total - 1}
        onClick={() => onMove(1)} aria-label={`Move ${title} down`}><ArrowDown className="h-4 w-4" /></button>
    </Reorder.Item>
  );
}

export function CustomizePanel({ widgets, onChange }: Props) {
  function move(index: number, dir: -1 | 1) {
    const next = [...widgets];
    const target = index + dir;
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }
  return (
    <div className="glass mb-5 rounded-2xl p-4">
      <p className="mb-3 text-sm text-dim">Drag to reorder, or use the arrows. Untick a widget to hide it.</p>
      <Reorder.Group axis="y" values={widgets} onReorder={onChange} className="space-y-2">
        {widgets.map((w, i) => (
          <Item key={w.id} w={w} index={i} total={widgets.length}
            onToggle={() => onChange(widgets.map((x) => (x.id === w.id ? { ...x, visible: !x.visible } : x)))}
            onMove={(dir) => move(i, dir)} />
        ))}
      </Reorder.Group>
    </div>
  );
}

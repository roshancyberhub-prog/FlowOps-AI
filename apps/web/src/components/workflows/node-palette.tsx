"use client";
import { Plus } from "lucide-react";
import type { NodeSpec } from "@/lib/workflows";
export function NodePalette({
  specs,
  readOnly,
  onAdd,
}: {
  specs: NodeSpec[];
  readOnly: boolean;
  onAdd: (type: string) => void;
}) {
  return (
    <aside className="border-b border-slate-200 bg-white p-4 xl:max-h-[600px] xl:overflow-auto xl:border-b-0 xl:border-r">
      <p className="eyebrow mb-3">Node library</p>
      {!readOnly ? (
        <>
          <label className="sr-only" htmlFor="add-node">
            Add a node
          </label>
          <select
            id="add-node"
            className="xl:hidden"
            value=""
            onChange={(event) => onAdd(event.target.value)}
          >
            <option value="">Choose a node…</option>
            {specs.map((spec) => (
              <option key={spec.type} value={spec.type}>
                {spec.title}
              </option>
            ))}
          </select>
          <div className="hidden space-y-2 xl:block">
            {specs.map((spec) => (
              <button
                key={spec.type}
                type="button"
                draggable
                onDragStart={(event) =>
                  event.dataTransfer.setData(
                    "application/flowops-node",
                    spec.type,
                  )
                }
                onClick={() => onAdd(spec.type)}
                className="flex w-full items-center gap-2 rounded-lg border border-slate-200 p-2.5 text-left text-xs hover:border-teal-400 hover:bg-teal-50"
              >
                <Plus size={13} className="shrink-0 text-teal-700" />
                {spec.title}
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="text-xs leading-6 text-slate-500">
          Published versions are immutable. Switch to the draft to make changes.
        </p>
      )}
    </aside>
  );
}

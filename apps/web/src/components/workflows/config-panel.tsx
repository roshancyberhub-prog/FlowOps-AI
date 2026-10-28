"use client";

import type { NodeSpec } from "@/lib/workflows";
import type { WorkflowCanvasNode } from "./workflow-node";
import { Button } from "@/components/ui/button";

export function ConfigPanel({
  node,
  spec,
  readOnly,
  onChange,
  onDelete,
}: {
  node?: WorkflowCanvasNode;
  spec?: NodeSpec;
  readOnly: boolean;
  onChange: (label: string, config: Record<string, unknown>) => void;
  onDelete: () => void;
}) {
  if (!node)
    return (
      <aside className="border-t border-slate-200 bg-white p-5 xl:border-l xl:border-t-0">
        <p className="eyebrow mb-3">Node settings</p>
        <p className="text-sm leading-6 text-slate-500">
          Select a node to inspect its settings. Connect nodes from their output
          handles to the next input.
        </p>
      </aside>
    );
  const update = (key: string, value: unknown) =>
    onChange(node.data.label, { ...node.data.config, [key]: value });
  return (
    <aside className="space-y-5 overflow-auto border-t border-slate-200 bg-white p-5 xl:max-h-[600px] xl:border-l xl:border-t-0">
      <div>
        <p className="eyebrow mb-2">Node settings</p>
        <h2 className="text-base font-semibold">
          {spec?.title ?? node.data.nodeType}
        </h2>
      </div>
      <div>
        <label htmlFor="node-label">Node label</label>
        <input
          id="node-label"
          maxLength={80}
          readOnly={readOnly}
          value={node.data.label}
          onChange={(event) => onChange(event.target.value, node.data.config)}
        />
      </div>
      {Object.entries(spec?.config_schema.properties ?? {}).map(
        ([key, property]) => {
          const value = node.data.config[key] ?? property.default ?? "";
          const numeric =
            property.type === "number" ||
            property.type === "integer" ||
            (key === "value" &&
              ["gt", "gte", "lt", "lte"].includes(
                String(node.data.config.operator),
              ));
          if (
            key === "value" &&
            ["exists", "missing"].includes(String(node.data.config.operator))
          )
            return null;
          return (
            <div key={key}>
              <label htmlFor={`config-${key}`}>
                {property.title ?? key.replaceAll("_", " ")}
              </label>
              {property.enum ? (
                <select
                  id={`config-${key}`}
                  disabled={readOnly}
                  value={String(value)}
                  onChange={(event) => update(key, event.target.value)}
                >
                  {property.enum.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              ) : (
                <input
                  id={`config-${key}`}
                  readOnly={readOnly}
                  type={numeric ? "number" : "text"}
                  min={property.minimum}
                  max={property.maximum}
                  value={String(value)}
                  onChange={(event) =>
                    update(
                      key,
                      numeric ? Number(event.target.value) : event.target.value,
                    )
                  }
                />
              )}
              {property.description && (
                <p className="mt-2 text-xs text-slate-500">
                  {property.description}
                </p>
              )}
            </div>
          );
        },
      )}
      {!Object.keys(spec?.config_schema.properties ?? {}).length && (
        <p className="text-xs text-slate-500">
          This node has no additional options.
        </p>
      )}
      {!readOnly && (
        <Button
          variant="outline"
          className="w-full text-red-700"
          onClick={onDelete}
        >
          Remove node
        </Button>
      )}
    </aside>
  );
}

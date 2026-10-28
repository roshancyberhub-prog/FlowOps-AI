"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { GitBranch, Play, Zap } from "lucide-react";

export type WorkflowCanvasNode = Node<
  {
    nodeType: string;
    label: string;
    config: Record<string, unknown>;
    category: string;
    outputs: string[];
  },
  "flowops"
>;

export function WorkflowNode({
  data,
  selected,
  isConnectable,
}: NodeProps<WorkflowCanvasNode>) {
  const Icon =
    data.category === "trigger"
      ? Play
      : data.category === "condition"
        ? GitBranch
        : Zap;
  return (
    <div
      data-testid="workflow-node"
      className={`w-48 rounded-xl border bg-white p-4 shadow-sm ${selected ? "border-teal-600 ring-2 ring-teal-100" : "border-slate-300"}`}
    >
      {data.category !== "trigger" && (
        <Handle
          type="target"
          position={Position.Left}
          isConnectable={isConnectable}
        />
      )}
      <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
        <Icon size={14} className="text-teal-700" />
        {data.category}
      </div>
      <p className="text-sm font-semibold text-slate-800">{data.label}</p>
      {data.outputs.map((handle, index) => (
        <Handle
          key={handle}
          id={handle}
          type="source"
          position={Position.Right}
          isConnectable={isConnectable}
          style={{
            top: data.outputs.length > 1 ? `${35 + index * 40}%` : "50%",
          }}
          aria-label={`${handle} output`}
        />
      ))}
      {data.category === "condition" && (
        <div className="mt-3 flex justify-between text-[10px] text-slate-500">
          <span>True ↗</span>
          <span>False ↘</span>
        </div>
      )}
    </div>
  );
}

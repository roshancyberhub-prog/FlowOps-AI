"use client";

import { useRef } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import { WorkflowNode } from "./workflow-node";
import { ConfigPanel } from "./config-panel";
import { NodePalette } from "./node-palette";
import { WorkflowToolbar } from "./toolbar";
import { useWorkflowCanvas } from "./use-workflow-canvas";
import type { CanvasProps } from "./types";
import "@xyflow/react/dist/style.css";
const nodeTypes = { flowops: WorkflowNode };
export function WorkflowCanvas(props: CanvasProps) {
  return (
    <ReactFlowProvider>
      <Canvas {...props} />
    </ReactFlowProvider>
  );
}
function Canvas(props: CanvasProps) {
  const { specs, readOnly } = props;
  const state = useWorkflowCanvas(props);
  const canvasRef = useRef<HTMLDivElement>(null);
  const {
    nodes,
    edges,
    instance,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    active,
    selected,
    setSelected,
    setNodes,
    setEdges,
    markDirty,
  } = state;
  return (
    <>
      <WorkflowToolbar state={state} readOnly={readOnly} />
      <section
        aria-label="Visual workflow editor"
        className="panel grid min-w-0 overflow-hidden xl:grid-cols-[170px_minmax(0,1fr)_250px]"
      >
        <NodePalette
          specs={specs}
          readOnly={readOnly}
          onAdd={(type) => {
            const bounds = canvasRef.current?.getBoundingClientRect();
            addNode(
              type,
              bounds
                ? instance.screenToFlowPosition({
                    x: bounds.left + bounds.width / 2 - 96,
                    y: bounds.top + bounds.height / 2 - 40,
                  })
                : undefined,
            );
          }}
        />
        <div
          ref={canvasRef}
          className="relative min-w-0 bg-slate-50"
          style={{ height: 600 }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            addNode(
              event.dataTransfer.getData("application/flowops-node"),
              instance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
              }),
            );
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => setSelected(node.id)}
            nodesDraggable={!readOnly}
            nodesConnectable={!readOnly}
            edgesReconnectable={false}
            deleteKeyCode={readOnly ? null : ["Backspace", "Delete"]}
            fitView
            minZoom={0.2}
            maxZoom={1.5}
          >
            <Background gap={20} color="#d5dfe5" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
        <ConfigPanel
          node={active}
          spec={specs.find((spec) => spec.type === active?.data.nodeType)}
          readOnly={readOnly}
          onChange={(label, config) => {
            setNodes((current) =>
              current.map((node) =>
                node.id === selected
                  ? { ...node, data: { ...node.data, label, config } }
                  : node,
              ),
            );
            markDirty();
          }}
          onDelete={() => {
            setNodes((current) =>
              current.filter((node) => node.id !== selected),
            );
            setEdges((current) =>
              current.filter(
                (edge) => edge.source !== selected && edge.target !== selected,
              ),
            );
            setSelected(undefined);
            markDirty();
          }}
        />
      </section>
      <p className="mt-4 text-xs text-slate-500">
        Use one trigger and one connection per output. Loops and joining
        branches are not supported. Running workflows is not available in this
        release.
      </p>
    </>
  );
}

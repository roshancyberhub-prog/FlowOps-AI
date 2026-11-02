"use client";
import { useCallback, useEffect, useState } from "react";
import {
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type NodeChange,
} from "@xyflow/react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  ValidationResult,
  Workflow,
  WorkflowGraph,
} from "@/lib/workflows";
import { useWorkspace } from "@/components/workspace";
import type { WorkflowCanvasNode } from "./workflow-node";
import type { CanvasProps } from "./types";
export function useWorkflowCanvas({
  workflow,
  graph,
  specs,
  readOnly,
  onSaved,
  onDirtyChange,
}: CanvasProps) {
  const { organization } = useWorkspace();
  const instance = useReactFlow<WorkflowCanvasNode>();
  const [nodes, setNodes, changeNodes] = useNodesState<WorkflowCanvasNode>(
    graph.nodes.map((node) => {
      const spec = specs.find((item) => item.type === node.type);
      return {
        id: node.id,
        type: "flowops",
        position: node.position,
        data: {
          nodeType: node.type,
          label: node.label ?? spec?.title ?? node.type,
          config: node.config,
          category: spec?.category ?? "action",
          outputs: spec?.outputs ?? ["default"],
        },
      };
    }),
  );
  const [edges, setEdges, changeEdges] = useEdgesState<Edge>(
    graph.edges.map((edge, index) => ({
      ...edge,
      id: edge.id ?? `edge_${index}`,
      sourceHandle: edge.sourceHandle ?? "default",
    })),
  );
  const [name, setName] = useState(workflow.name);
  const [selected, setSelected] = useState<string>();
  const [dirty, setDirty] = useState(false);
  const definition = (): WorkflowGraph => ({
    schema_version: 1,
    nodes: nodes.map((node) => ({
      id: node.id,
      type: node.data.nodeType,
      label: node.data.label,
      config: node.data.config,
      position: node.position,
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
    })),
  });
  const validate = useMutation({
    mutationFn: () =>
      api<ValidationResult>(
        `/workflows/${workflow.id}/validate`,
        { method: "POST", body: JSON.stringify(definition()) },
        organization.id,
      ),
  });
  const save = useMutation({
    mutationFn: () =>
      api<Workflow>(
        `/workflows/${workflow.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            expected_revision: workflow.revision,
            name,
            graph: definition(),
          }),
        },
        organization.id,
      ),
    onSuccess: (result) => {
      setDirty(false);
      onSaved(result, "Draft saved.");
    },
  });
  const publish = useMutation({
    mutationFn: () =>
      api<Workflow>(
        `/workflows/${workflow.id}/publish`,
        {
          method: "POST",
          body: JSON.stringify({ expected_revision: workflow.revision }),
        },
        organization.id,
      ),
    onSuccess: (result) => {
      onSaved(result, `Version ${result.version_number} published.`);
    },
  });
  const markDirty = useCallback(() => {
    setDirty(true);
    onDirtyChange(true);
    validate.reset();
  }, [validate, onDirtyChange]);
  useEffect(() => {
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    const navigate = (event: MouseEvent) => {
      const anchor = (event.target as Element).closest("a[href]");
      if (
        anchor &&
        !window.confirm("Leave this workflow and discard unsaved changes?")
      ) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", navigate, true);
    return () => {
      window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", navigate, true);
    };
  }, [dirty]);
  const onConnect = (connection: Connection) => {
    if (!readOnly) {
      setEdges((current) =>
        addEdge({ ...connection, id: crypto.randomUUID() }, current),
      );
      markDirty();
    }
  };
  const onNodesChange = (changes: NodeChange<WorkflowCanvasNode>[]) => {
    changeNodes(changes);
    if (
      changes.some((change) => !["select", "dimensions"].includes(change.type))
    )
      markDirty();
  };
  const onEdgesChange = (changes: EdgeChange<Edge>[]) => {
    changeEdges(changes);
    if (changes.some((change) => change.type !== "select")) markDirty();
  };
  const addNode = (
    type: string,
    position = instance.screenToFlowPosition({
      x: window.innerWidth / 2,
      y: 350,
    }),
  ) => {
    const spec = specs.find((item) => item.type === type);
    if (!spec || readOnly) return;
    const id = crypto.randomUUID();
    const config = Object.fromEntries(
      Object.entries(spec.config_schema.properties)
        .filter(([, field]) => field.default !== undefined)
        .map(([key, field]) => [key, field.default]),
    );
    setNodes((current) => [
      ...current,
      {
        id,
        type: "flowops",
        position,
        data: {
          nodeType: type,
          label: spec.title,
          config,
          category: spec.category,
          outputs: spec.outputs,
        },
      },
    ]);
    setSelected(id);
    markDirty();
  };
  const active = nodes.find((node) => node.id === selected);
  const error = save.error ?? publish.error ?? validate.error;
  return {
    instance,
    nodes,
    edges,
    setNodes,
    setEdges,
    name,
    setName,
    dirty,
    selected,
    setSelected,
    validate,
    save,
    publish,
    markDirty,
    onConnect,
    onNodesChange,
    onEdgesChange,
    addNode,
    active,
    error,
  };
}

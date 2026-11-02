import type { NodeSpec, Workflow, WorkflowGraph } from "@/lib/workflows";
export type CanvasProps = {
  workflow: Workflow;
  graph: WorkflowGraph;
  specs: NodeSpec[];
  readOnly: boolean;
  onSaved: (workflow: Workflow, message: string) => void;
  onDirtyChange: (dirty: boolean) => void;
};

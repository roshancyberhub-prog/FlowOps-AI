export type WorkflowGraph = {
  schema_version: 1;
  nodes: {
    id: string;
    type: string;
    label?: string | null;
    config: Record<string, unknown>;
    position: { x: number; y: number };
  }[];
  edges: {
    id?: string | null;
    source: string;
    target: string;
    sourceHandle?: string | null;
  }[];
};
export type Workflow = {
  id: string;
  name: string;
  description: string;
  status: "draft" | "active" | "paused" | "archived";
  draft_graph: WorkflowGraph;
  current_version_id: string | null;
  version_number: number;
  revision: number;
  updated_at: string;
};
export type WorkflowVersion = {
  id: string;
  version_number: number;
  graph_definition: WorkflowGraph;
  created_at: string;
};
export type ValidationResult = {
  valid: boolean;
  order: string[];
  errors: { code: string; message: string; node_id: string | null }[];
};
export type ConfigProperty = {
  title?: string;
  type?: string;
  default?: unknown;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  description?: string;
};
export type NodeSpec = {
  type: string;
  title: string;
  category: "trigger" | "condition" | "action";
  can_publish: boolean;
  outputs: string[];
  config_schema: {
    properties: Record<string, ConfigProperty>;
    required?: string[];
  };
};

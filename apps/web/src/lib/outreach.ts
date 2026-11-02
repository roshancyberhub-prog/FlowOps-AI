export type ProviderStatus = {
  ai_provider: "disabled" | "mock";
  email_provider: "disabled" | "mock";
  live_ai_available: boolean;
  live_email_available: boolean;
};
export type Draft = {
  id: string;
  lead_id: string | null;
  execution_id: string;
  recipient: string;
  subject: string;
  body: string;
  qualification: {
    fit_category: string;
    confidence: number;
    reasoning_summary: string;
    missing_information: string[];
    recommended_next_step: string;
  };
  provided_facts: Record<string, unknown>;
  ai_metadata: Record<
    string,
    {
      provider: string;
      model: string;
      prompt_version: string;
      simulated: boolean;
      usage: Record<string, number>;
    }
  >;
  revision: number;
  status: string;
  execution_status: string;
  last_edited_by: string | null;
  created_at: string;
  updated_at: string;
};
export type Delivery = {
  id: string;
  execution_id: string;
  draft_id: string;
  provider: string;
  provider_message_id: string;
  status: string;
  recipient: string;
  delivery_metadata: { simulated: boolean; external_message_sent: boolean };
  created_at: string;
};
export type DraftWorkflow = {
  workflow_id: string;
  name: string;
  version_id: string;
  version_number: number;
  can_run: boolean;
};

export type ScoringConfig = {
  schema_version: 1;
  target_titles: string[];
  target_industries: string[];
  target_company_sizes: string[];
  personal_email_domains: string[];
  required_fields: string[];
  title_weight: number;
  industry_weight: number;
  size_weight: number;
  business_email_weight: number;
  website_weight: number;
  missing_penalty: number;
};
export type ScoringProfile = {
  id: string;
  name: string;
  version_number: number;
  configuration: ScoringConfig;
  created_at: string;
};

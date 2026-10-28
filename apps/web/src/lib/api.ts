export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  organization?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams)
  )
    headers.set("Content-Type", "application/json");
  if (organization) headers.set("X-Organization-ID", organization);
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.error?.details
      ?.map((item: { message: string }) => item.message)
      .join(" ");
    throw new ApiError(
      response.status,
      detail ||
        payload.error?.message ||
        "The request failed. Please try again.",
    );
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}

export type User = { id: string; email: string; display_name: string };
export type Organization = {
  id: string;
  name: string;
  role: "owner" | "admin" | "member" | "viewer";
};
export type Lead = {
  id: string;
  name: string;
  email: string;
  company: string | null;
  job_title: string | null;
  industry: string | null;
  website: string | null;
  company_size: string | null;
  country: string | null;
  source: string | null;
  status: string;
  score: number;
  score_reasons: string[];
  created_at: string;
  updated_at: string;
};
export type LeadPage = {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
};

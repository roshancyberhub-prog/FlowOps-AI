"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScoringConfig, ScoringProfile } from "@/lib/scoring";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";
import { QueryFeedback } from "@/features/executions/shared";

export default function ScoringPage() {
  const { organization } = useWorkspace();
  const profile = useQuery({
    queryKey: ["scoring-profile", organization.id],
    queryFn: () =>
      api<ScoringProfile>("/scoring-profiles/current", {}, organization.id),
  });
  return (
    <>
      <p className="eyebrow mb-2">Make fit explainable</p>
      <h1 className="text-3xl font-semibold tracking-tight">
        Scoring profiles
      </h1>
      <p className="mb-6 mt-2 max-w-3xl text-slate-500">
        Set your ideal customer signals. A score is the sum of matching rules,
        clamped to 0–100. These example weights are not validated business
        benchmarks.
      </p>
      <QueryFeedback
        pending={profile.isPending}
        error={profile.error}
        retry={() => profile.refetch()}
      />
      {profile.data && (
        <ProfileEditor key={profile.data.id} profile={profile.data} />
      )}
    </>
  );
}
const listFields = [
  { key: "target_titles", label: "Target job title phrases" },
  { key: "target_industries", label: "Target industries" },
  { key: "target_company_sizes", label: "Target company sizes" },
  { key: "personal_email_domains", label: "Personal email domains" },
] as const;
const weightFields = [
  { key: "title_weight", label: "Job title match" },
  { key: "industry_weight", label: "Industry match" },
  { key: "size_weight", label: "Company size match" },
  { key: "business_email_weight", label: "Business email heuristic" },
  { key: "website_weight", label: "Website present" },
  { key: "missing_penalty", label: "Missing required fields (applied once)" },
] as const;
function ProfileEditor({ profile }: { profile: ScoringProfile }) {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const [name, setName] = useState(profile.name);
  const [lists, setLists] = useState(
    () =>
      Object.fromEntries(
        listFields.map((field) => [
          field.key,
          profile.configuration[field.key].join(", "),
        ]),
      ) as Record<(typeof listFields)[number]["key"], string>,
  );
  const [config, setConfig] = useState(profile.configuration);
  const [weights, setWeights] = useState(
    () =>
      Object.fromEntries(
        weightFields.map((field) => [
          field.key,
          String(profile.configuration[field.key]),
        ]),
      ) as Record<(typeof weightFields)[number]["key"], string>,
  );
  const writable = ["owner", "admin"].includes(organization.role);
  const save = useMutation({
    mutationFn: () => {
      const configuration: ScoringConfig = {
        ...config,
        ...Object.fromEntries(
          weightFields.map((field) => [field.key, Number(weights[field.key])]),
        ),
        ...Object.fromEntries(
          listFields.map((field) => [
            field.key,
            lists[field.key]
              .split(",")
              .map((v) => v.trim())
              .filter(Boolean),
          ]),
        ),
      };
      return api<ScoringProfile>(
        "/scoring-profiles",
        { method: "POST", body: JSON.stringify({ name, configuration }) },
        organization.id,
      );
    },
    onSuccess: (result) =>
      client.setQueryData(["scoring-profile", organization.id], result),
  });
  return (
    <form
      className="panel max-w-4xl p-6"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate();
      }}
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">
          Current profile · Version {profile.version_number}
        </h2>
        <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
          Immutable version
        </span>
      </div>
      <p className="mb-6 text-sm text-slate-500">
        Saving creates a new version. Published workflows keep their pinned
        profile. Existing lead scores remain visible until recalculated or their
        input fields change.
      </p>
      <div className="max-w-md">
        <label htmlFor="profile-name">Profile name</label>
        <input
          id="profile-name"
          value={name}
          required
          maxLength={100}
          readOnly={!writable}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="mt-5 grid gap-5 md:grid-cols-2">
        {listFields.map((field) => (
          <div key={field.key}>
            <label htmlFor={field.key}>{field.label}</label>
            <textarea
              id={field.key}
              value={lists[field.key]}
              readOnly={!writable}
              maxLength={10000}
              onChange={(e) =>
                setLists({ ...lists, [field.key]: e.target.value })
              }
            />
            <p className="mt-1 text-xs text-slate-500">
              Comma-separated. Industries and sizes match exactly; title phrases
              use word boundaries. Matching ignores case.
            </p>
          </div>
        ))}
      </div>
      <fieldset className="mt-6">
        <legend className="mb-3 text-sm font-semibold">
          Points per signal
        </legend>
        <div className="grid gap-4 sm:grid-cols-3">
          {weightFields.map((field) => (
            <div key={field.key}>
              <label htmlFor={field.key}>{field.label}</label>
              <input
                type="number"
                id={field.key}
                min={field.key === "missing_penalty" ? -100 : 0}
                max={field.key === "missing_penalty" ? 0 : 100}
                required
                step={1}
                readOnly={!writable}
                value={weights[field.key]}
                onChange={(e) =>
                  setWeights({ ...weights, [field.key]: e.target.value })
                }
              />
            </div>
          ))}
        </div>
      </fieldset>
      <fieldset className="mt-6">
        <legend className="mb-3 text-sm font-semibold">Required fields</legend>
        <div className="flex flex-wrap gap-4">
          {[
            "company",
            "job_title",
            "industry",
            "company_size",
            "website",
            "country",
          ].map((field) => (
            <label key={field} className="flex items-center gap-2">
              <input
                type="checkbox"
                disabled={!writable}
                checked={config.required_fields.includes(field)}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    required_fields: e.target.checked
                      ? [...config.required_fields, field]
                      : config.required_fields.filter((v) => v !== field),
                  })
                }
              />
              {field.replaceAll("_", " ")}
            </label>
          ))}
        </div>
      </fieldset>
      <p className="mt-5 text-xs text-slate-500">
        The email signal checks a configurable personal-domain list. It does not
        verify ownership or deliverability.
      </p>
      {save.error && (
        <p role="alert" className="notice mt-4">
          {save.error.message}
        </p>
      )}
      {writable && (
        <Button className="mt-6" disabled={save.isPending || !name.trim()}>
          {save.isPending ? "Saving…" : "Save new profile version"}
        </Button>
      )}
    </form>
  );
}

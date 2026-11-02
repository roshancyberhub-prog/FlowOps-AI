"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Lead } from "@/lib/api";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

export function LeadScoring({ lead }: { lead: Lead }) {
  const { organization } = useWorkspace();
  const client = useQueryClient();
  const details = useQuery({
    queryKey: ["lead", organization.id, lead.id],
    queryFn: () => api<Lead>(`/leads/${lead.id}`, {}, organization.id),
    initialData: lead,
  });
  const score = useMutation({
    mutationFn: () =>
      api<Lead>(
        `/leads/${lead.id}/score`,
        { method: "POST", body: "{}" },
        organization.id,
      ),
    onSuccess: (result) => {
      client.setQueryData(["lead", organization.id, lead.id], result);
      client.invalidateQueries({ queryKey: ["leads", organization.id] });
    },
  });
  const result = details.data;
  return (
    <section
      className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4"
      aria-label="Lead score"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">ICP fit score</h3>
          <p className="mt-1 text-xs text-slate-500">
            Transparent rules · Example weights, not a conversion prediction
          </p>
        </div>
        <p className="text-2xl font-semibold text-teal-800">
          {result.scored_at ? `${result.score} / 100` : "Not scored"}
        </p>
      </div>
      {result.scored_at && (
        <>
          <p className="mt-3 text-xs text-slate-500">
            Profile version {result.score_profile_version} ·{" "}
            {new Date(result.scored_at).toLocaleString()}
          </p>
          <ul className="mt-4 space-y-3">
            {result.score_reasons.map((reason) => (
              <li key={reason.rule} className="flex gap-3 text-xs">
                <span className="w-8 shrink-0 font-semibold">
                  {reason.points > 0 ? "+" : ""}
                  {reason.points}
                </span>
                <span className="text-slate-600">{reason.reason}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {organization.role !== "viewer" && result.status !== "archived" && (
        <Button
          type="button"
          variant="outline"
          className="mt-4"
          disabled={score.isPending}
          onClick={() => score.mutate()}
        >
          {score.isPending ? "Calculating…" : "Calculate with current profile"}
        </Button>
      )}
      {(score.error || details.error) && (
        <p role="alert" className="notice mt-3">
          {(score.error || details.error)?.message}
        </p>
      )}
    </section>
  );
}

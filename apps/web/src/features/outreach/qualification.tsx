import type { Draft } from "@/lib/outreach";
import { Status } from "@/features/executions/shared";

export function QualificationPanel({ draft }: { draft: Draft }) {
  const result = draft.qualification;
  return (
    <section className="panel p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">Qualification</h2>
        <Status value={result.fit_category} />
      </div>
      <p className="mt-4 whitespace-pre-wrap break-words text-sm text-slate-600">
        {result.reasoning_summary}
      </p>
      <p className="mt-3 text-xs text-slate-500">
        {draft.ai_metadata.qualification.simulated
          ? "Mock estimate"
          : "Provider-reported estimate"}
        : {result.confidence.toFixed(2)}. This is not a conversion prediction.
      </p>
      <h3 className="mt-5 text-sm font-semibold">Missing information</h3>
      {result.missing_information.length ? (
        <ul className="mt-2 list-inside list-disc text-sm text-slate-600">
          {result.missing_information.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-500">
          No missing fields reported by this provider.
        </p>
      )}
      <p className="mt-4 text-sm text-slate-600">
        Next step: {result.recommended_next_step}
      </p>
      <details className="mt-5 text-xs">
        <summary className="cursor-pointer font-semibold text-teal-800">
          Provided fields · not externally verified
        </summary>
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-3">
          {JSON.stringify(draft.provided_facts, null, 2)}
        </pre>
      </details>
      <details className="mt-3 text-xs">
        <summary className="cursor-pointer font-semibold text-teal-800">
          Provider, prompts, and usage
        </summary>
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-3">
          {JSON.stringify(draft.ai_metadata, null, 2)}
        </pre>
      </details>
    </section>
  );
}

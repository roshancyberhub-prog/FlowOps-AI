import { Button } from "@/components/ui/button";
import { humanize } from "@/lib/executions";

export function Status({ value }: { value: string }) {
  const colors =
    value === "succeeded" || value === "approved"
      ? "bg-teal-50 text-teal-800"
      : value === "failed" || value === "rejected"
        ? "bg-red-50 text-red-800"
        : "bg-slate-100 text-slate-700";
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold capitalize ${colors}`}
    >
      {humanize(value)}
    </span>
  );
}
export function QueryFeedback({
  pending,
  error,
  retry,
}: {
  pending: boolean;
  error: Error | null;
  retry: () => void;
}) {
  if (pending)
    return (
      <p className="p-6" aria-busy>
        Loading records…
      </p>
    );
  if (error)
    return (
      <div className="p-6">
        <p role="alert" className="notice">
          {error.message}
        </p>
        <Button variant="outline" className="mt-3" onClick={retry}>
          Try again
        </Button>
      </div>
    );
  return null;
}
export function Pagination({
  page,
  total,
  size,
  change,
}: {
  page: number;
  total: number;
  size: number;
  change: (page: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 border-t border-slate-200 p-4">
      <Button
        variant="outline"
        disabled={page === 1}
        onClick={() => change(page - 1)}
      >
        Previous
      </Button>
      <span className="text-xs text-slate-500">
        Page {page} · {total} records
      </span>
      <Button
        variant="outline"
        disabled={page * size >= total}
        onClick={() => change(page + 1)}
      >
        Next
      </Button>
    </div>
  );
}

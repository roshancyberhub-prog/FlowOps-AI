"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Delivery } from "@/lib/outreach";
import type { Page } from "@/lib/executions";
import { useWorkspace } from "@/components/workspace";
import {
  Pagination,
  QueryFeedback,
  Status,
} from "@/features/executions/shared";

export function DeliveryHistory({
  executionId,
  draftId,
  active = false,
}: {
  executionId?: string;
  draftId?: string;
  active?: boolean;
}) {
  const { organization } = useWorkspace();
  const [page, setPage] = useState(1);
  const client = useQueryClient();
  const params = new URLSearchParams({ page: String(page) });
  if (executionId) params.set("execution_id", executionId);
  if (draftId) params.set("draft_id", draftId);
  const receipts = useQuery({
    queryKey: [
      "deliveries",
      organization.id,
      executionId ?? "",
      draftId ?? "",
      page,
    ],
    queryFn: () =>
      api<Page<Delivery>>(`/deliveries?${params}`, {}, organization.id),
    refetchInterval: active ? 3000 : false,
  });
  useEffect(() => {
    if (!active)
      client.invalidateQueries({
        queryKey: [
          "deliveries",
          organization.id,
          executionId ?? "",
          draftId ?? "",
        ],
      });
  }, [active, client, organization.id, executionId, draftId]);
  return (
    <section className="panel mt-6 overflow-hidden">
      <div className="border-b border-slate-200 p-5">
        <h2 className="font-semibold">Email delivery receipts</h2>
      </div>
      <QueryFeedback
        pending={receipts.isPending}
        error={receipts.error}
        retry={() => receipts.refetch()}
      />
      {receipts.data && (
        <>
          {!receipts.data.items.length ? (
            <p className="p-6 text-sm text-slate-500">
              No delivery receipt has been recorded.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {receipts.data.items.map((receipt) => (
                <li key={receipt.id} className="p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="break-all font-semibold">
                      {receipt.recipient}
                    </p>
                    <Status value={receipt.status} />
                  </div>
                  <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
                    {receipt.delivery_metadata.simulated
                      ? "Mock receipt · No external email was sent."
                      : "Provider receipt recorded."}
                  </p>
                  <p className="mt-3 break-all text-xs text-slate-500">
                    Provider: {receipt.provider} · {receipt.provider_message_id}
                    <br />
                    {new Date(receipt.created_at).toLocaleString()}
                  </p>
                  <Link
                    className="mt-3 inline-block text-xs font-semibold text-teal-800 hover:underline"
                    href={`/drafts/${receipt.draft_id}`}
                  >
                    View reviewed draft →
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Pagination
            page={page}
            total={receipts.data.total}
            size={25}
            change={setPage}
          />
        </>
      )}
    </section>
  );
}

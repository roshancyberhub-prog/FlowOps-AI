"use client";
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/outreach";
import { useWorkspace } from "@/components/workspace";
import { Button } from "@/components/ui/button";

export function DraftEditor({
  draft,
  onSaved,
  onCancel,
}: {
  draft: Draft;
  onSaved: (draft: Draft) => void;
  onCancel: () => void;
}) {
  const { organization } = useWorkspace();
  const [data, setData] = useState(() => ({
    expected_revision: draft.revision,
    subject: draft.subject,
    body: draft.body,
  }));
  const dirty = data.subject !== draft.subject || data.body !== draft.body;
  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);
  const save = useMutation({
    mutationFn: () =>
      api<Draft>(
        `/drafts/${draft.id}`,
        { method: "PATCH", body: JSON.stringify(data) },
        organization.id,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
        Saving changes creates a new draft revision and invalidates any older
        pending approval. The recipient stays fixed.
      </p>
      <div>
        <label htmlFor="draft-subject">Subject</label>
        <input
          id="draft-subject"
          value={data.subject}
          required
          maxLength={160}
          onChange={(event) =>
            setData({ ...data, subject: event.target.value })
          }
        />
      </div>
      <div>
        <label htmlFor="draft-body">Message body</label>
        <textarea
          id="draft-body"
          value={data.body}
          required
          maxLength={4000}
          rows={10}
          onChange={(event) => setData({ ...data, body: event.target.value })}
        />
      </div>
      {save.error && (
        <p role="alert" className="notice">
          {save.error.message}
        </p>
      )}
      <div className="flex gap-3">
        <Button disabled={save.isPending || !dirty}>
          {save.isPending ? "Saving…" : "Save draft revision"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={save.isPending}
          onClick={onCancel}
        >
          Cancel editing
        </Button>
      </div>
    </form>
  );
}

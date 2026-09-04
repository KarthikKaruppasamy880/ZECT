import { useCallback, useEffect, useRef, useState } from "react";
import { getDocumentMarkdown, linkAttachmentToWorkItem, uploadDocument, uploadImageAttachment } from "@/lib/api";

/** File extensions the document-intelligence pipeline can turn into text
 * context (see backend/app/services/document_intelligence/service.py
 * ALLOWED_EXT). Images are handled separately -- see imageDataUrlFromFile. */
export const COMPOSER_DOCUMENT_ACCEPT =
  ".txt,.md,.markdown,.json,.yaml,.yml,.xml,.log,.py,.ts,.tsx,.js,.jsx,.go,.rs,.java,.sql,.sh,.ps1,.docx,.pdf,.pptx";

export const COMPOSER_IMAGE_ACCEPT = ".png,.jpg,.jpeg,.gif,.webp";

export type ComposerAttachment = { id: number; filename: string; markdown: string };

const MAX_IMAGE_BYTES = 9 * 1024 * 1024;

export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

/** Reads an image File as a data:image/...;base64,... URL, ready to send as
 * vision content (see llm_phase.run_ask). Rejects anything implausibly large
 * client-side so a giant paste fails fast instead of hitting the server's
 * own size guard after a slow upload. */
export function imageDataUrlFromFile(file: File): Promise<string> {
  if (file.size > MAX_IMAGE_BYTES) {
    return Promise.reject(new Error(`${file.name} is too large to attach (max 9MB)`));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Failed to read image"));
    reader.readAsDataURL(file);
  });
}

/** Extracts any pasted image files from a clipboard paste event (e.g. a
 * screenshot copied to the clipboard) -- separate from normal text paste,
 * which the browser already handles natively for a textarea. */
export function imageFilesFromClipboard(e: React.ClipboardEvent): File[] {
  const items = e.clipboardData?.items;
  if (!items) return [];
  const files: File[] = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.kind === "file" && item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) files.push(file);
    }
  }
  return files;
}

export type ComposerImage = { id: string; filename: string; dataUrl: string; artifactId?: number };

/** Shared attachment state for the Mentrix composer (Ask/Plan/Agent): text
 * documents go through the existing upload -> markdown-extraction pipeline
 * (uploadDocument/getDocumentMarkdown); images upload durably too (not just
 * held as an in-memory data URL) so a screenshot survives a refresh. Both
 * are linked to `workItemId` as soon as it's known -- the first ASK turn
 * often attaches a file *before* a WorkItem exists yet, so linking happens
 * retroactively rather than at upload time. Once linked, the SAME artifact
 * is visible to every pane via listWorkItemAttachments -- no re-upload. */
export function useComposerAttachments(projectId?: number | null, workItemId?: number | null) {
  const [attachments, setAttachments] = useState<ComposerAttachment[]>([]);
  const [images, setImages] = useState<ComposerImage[]>([]);
  const [attaching, setAttaching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const linkedRef = useRef<Set<number>>(new Set());

  const attachDocument = useCallback(
    async (file: File) => {
      setAttaching(true);
      setError(null);
      try {
        const { artifact } = await uploadDocument({
          file,
          projectId: projectId ?? undefined,
          workItemId: workItemId ?? undefined,
        });
        if (workItemId != null) linkedRef.current.add(artifact.id);
        const doc = await getDocumentMarkdown(artifact.id);
        setAttachments((prev) => [...prev, { id: artifact.id, filename: file.name, markdown: doc.markdown || "" }]);
      } catch (e) {
        setError(e instanceof Error ? e.message : `Failed to attach ${file.name}`);
      } finally {
        setAttaching(false);
      }
    },
    [projectId, workItemId],
  );

  const attachImage = useCallback(
    async (file: File) => {
      setError(null);
      try {
        const dataUrl = await imageDataUrlFromFile(file);
        let artifactId: number | undefined;
        try {
          const { artifact } = await uploadImageAttachment({
            file,
            projectId: projectId ?? undefined,
            workItemId: workItemId ?? undefined,
          });
          artifactId = artifact.id;
          if (workItemId != null) linkedRef.current.add(artifact.id);
        } catch {
          // Durable persistence failing must never block the live vision
          // call -- the in-memory dataUrl below still works for this turn.
        }
        setImages((prev) => [
          ...prev,
          { id: `${file.name}-${prev.length}-${Date.now()}`, filename: file.name, dataUrl, artifactId },
        ]);
      } catch (e) {
        setError(e instanceof Error ? e.message : `Failed to attach ${file.name}`);
      }
    },
    [projectId, workItemId],
  );

  /** Links every not-yet-linked attachment to `id` right now, synchronously
   * with the caller's own knowledge of a just-resolved work_item_id --
   * critical for AskPane's ask(), which calls this and then attach.reset()
   * in the same call: waiting for the workItemId *prop* to come back down
   * from the parent would race reset() clearing local state first. */
  const linkPendingTo = useCallback(
    async (id: number) => {
      const pending = [
        ...attachments.map((a) => a.id),
        ...images.map((i) => i.artifactId).filter((aid): aid is number => aid != null),
      ].filter((aid) => !linkedRef.current.has(aid));
      await Promise.all(
        pending.map((aid) => {
          linkedRef.current.add(aid);
          return linkAttachmentToWorkItem(aid, id).catch(() => {
            linkedRef.current.delete(aid);
          });
        }),
      );
    },
    [attachments, images],
  );

  // Covers the case where workItemId simply arrives later as a prop without
  // going through this hook's own ask()-style flow (e.g. this pane wasn't
  // the one that resolved it).
  useEffect(() => {
    if (workItemId != null) void linkPendingTo(workItemId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workItemId]);

  /** Routes each file to the document or image path by content type. */
  const attachFiles = useCallback(
    async (files: FileList | File[], opts?: { allowImages?: boolean }) => {
      const allowImages = opts?.allowImages !== false;
      for (const file of Array.from(files)) {
        if (isImageFile(file)) {
          if (allowImages) await attachImage(file);
          else setError(`${file.name} is an image -- not supported as an attachment here`);
        } else {
          await attachDocument(file);
        }
      }
    },
    [attachDocument, attachImage],
  );

  const removeAttachment = useCallback((id: number) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const removeImage = useCallback((id: string) => {
    setImages((prev) => prev.filter((i) => i.id !== id));
  }, []);

  /** Text-document context, folded into the goal/plan/question text the
   * same way PlanPane already did before this attachment bar became shared. */
  const documentContextBlob = useCallback(() => {
    if (!attachments.length) return "";
    return attachments.map((a) => `[attachment:${a.filename}]\n${a.markdown}`).join("\n\n");
  }, [attachments]);

  const reset = useCallback(() => {
    setAttachments([]);
    setImages([]);
    setError(null);
  }, []);

  return {
    attachments,
    images,
    attaching,
    error,
    attachFiles,
    removeAttachment,
    removeImage,
    documentContextBlob,
    reset,
    setError,
    linkPendingTo,
  };
}

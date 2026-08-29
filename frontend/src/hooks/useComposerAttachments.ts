import { useCallback, useState } from "react";
import { getDocumentMarkdown, uploadDocument } from "@/lib/api";

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

/** Shared attachment state for the Mentrix composer (Ask/Plan/Agent): text
 * documents go through the existing upload -> markdown-extraction pipeline
 * (uploadDocument/getDocumentMarkdown); images are tracked separately as
 * data URLs for panes that pass them through as real vision content (Ask
 * today -- see developerAsk's `images` param). */
export function useComposerAttachments(projectId?: number | null) {
  const [attachments, setAttachments] = useState<ComposerAttachment[]>([]);
  const [images, setImages] = useState<{ id: string; filename: string; dataUrl: string }[]>([]);
  const [attaching, setAttaching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const attachDocument = useCallback(
    async (file: File) => {
      setAttaching(true);
      setError(null);
      try {
        const { artifact } = await uploadDocument({ file, projectId: projectId ?? undefined });
        const doc = await getDocumentMarkdown(artifact.id);
        setAttachments((prev) => [...prev, { id: artifact.id, filename: file.name, markdown: doc.markdown || "" }]);
      } catch (e) {
        setError(e instanceof Error ? e.message : `Failed to attach ${file.name}`);
      } finally {
        setAttaching(false);
      }
    },
    [projectId],
  );

  const attachImage = useCallback(async (file: File) => {
    setError(null);
    try {
      const dataUrl = await imageDataUrlFromFile(file);
      setImages((prev) => [...prev, { id: `${file.name}-${prev.length}-${Date.now()}`, filename: file.name, dataUrl }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to attach ${file.name}`);
    }
  }, []);

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
  };
}

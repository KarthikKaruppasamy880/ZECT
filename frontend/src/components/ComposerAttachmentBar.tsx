import { useState } from "react";
import { COMPOSER_DOCUMENT_ACCEPT, COMPOSER_IMAGE_ACCEPT } from "@/hooks/useComposerAttachments";

/**
 * Drag/drop + multi-file-picker attachment bar shared by Ask/Plan/Agent so
 * "no option to add files" isn't a per-tab gap. Composer-wide capability;
 * whether images actually reach the model as vision content depends on the
 * pane (Ask does today -- see useComposerAttachments/developerAsk).
 */
export function ComposerAttachmentBar({
  attachments,
  images,
  attaching,
  onAttachFiles,
  onRemoveAttachment,
  onRemoveImage,
  allowImages = true,
  testIdPrefix,
  hint,
}: {
  attachments: { id: number; filename: string }[];
  images: { id: string; filename: string; dataUrl: string }[];
  attaching: boolean;
  onAttachFiles: (files: FileList | File[]) => void;
  onRemoveAttachment: (id: number) => void;
  onRemoveImage: (id: string) => void;
  allowImages?: boolean;
  testIdPrefix: string;
  hint?: string;
}) {
  const [dragOver, setDragOver] = useState(false);
  const accept = allowImages ? `${COMPOSER_DOCUMENT_ACCEPT},${COMPOSER_IMAGE_ACCEPT}` : COMPOSER_DOCUMENT_ACCEPT;

  return (
    <div
      className={`mt-1 flex flex-wrap items-center gap-1.5 rounded border px-2 py-1 transition-colors ${
        dragOver ? "border-teal-400 bg-teal-50" : "border-slate-200"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (e.dataTransfer.files.length) onAttachFiles(e.dataTransfer.files);
      }}
      data-testid={`${testIdPrefix}-dropzone`}
    >
      <label className="cursor-pointer rounded border border-slate-300 px-2 py-0.5 text-[10px] text-slate-600 hover:bg-slate-50">
        {attaching ? "Uploading…" : "Attach files"}
        <input
          type="file"
          multiple
          className="hidden"
          data-testid={`${testIdPrefix}-attach-input`}
          accept={accept}
          onChange={(e) => {
            if (e.target.files?.length) onAttachFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      <span className="text-[10px] text-slate-400">
        {hint || (allowImages ? "or paste a screenshot / drag files here" : "or drag files here")}
      </span>
      {attachments.map((a) => (
        <span
          key={a.id}
          className="flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600"
          data-testid={`${testIdPrefix}-attachment-chip`}
        >
          {a.filename}
          <button
            type="button"
            onClick={() => onRemoveAttachment(a.id)}
            className="text-slate-400 hover:text-slate-700"
            aria-label={`Remove ${a.filename}`}
          >
            ×
          </button>
        </span>
      ))}
      {images.map((img) => (
        <span
          key={img.id}
          className="flex items-center gap-1 rounded bg-teal-50 px-1.5 py-0.5 text-[10px] text-teal-700"
          data-testid={`${testIdPrefix}-image-chip`}
        >
          <img src={img.dataUrl} alt={img.filename} className="h-4 w-4 rounded object-cover" />
          {img.filename}
          <button
            type="button"
            onClick={() => onRemoveImage(img.id)}
            className="text-teal-400 hover:text-teal-700"
            aria-label={`Remove ${img.filename}`}
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}

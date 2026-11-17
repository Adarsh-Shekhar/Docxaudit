/** Document upload (Phase 16.1): drag-and-drop or picker; client-side
 * validation (PDF/DOCX, ≤25 MB mirroring backend) with progress bar. */
import { useCallback, useRef, useState, type DragEvent, type ReactNode } from "react";
import { uploadDocument } from "@/api/documents";
import { errorMessage } from "@/api/client";
import { InlineSpinner } from "@/components/FullPageLoader";

const ACCEPTED_MIME = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);
const MAX_BYTES = 25 * 1024 * 1024; // mirrors backend MAX_UPLOAD_BYTES

interface DocumentUploadProps {
  onUploaded: (documentId: string) => void;
  onError: (message: string) => void;
}

export function DocumentUpload({ onUploaded, onError }: DocumentUploadProps): ReactNode {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validate = (file: File): string | null => {
    if (!ACCEPTED_MIME.has(file.type)) return "Only PDF or DOCX files are supported.";
    if (file.size === 0) return "File is empty.";
    if (file.size > MAX_BYTES) return "File is larger than 25 MB.";
    return null;
  };

  const handleFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      const problem = validate(file);
      if (problem) {
        setValidationError(problem);
        return;
      }
      setValidationError(null);
      setProgress(0);
      try {
        const doc = await uploadDocument(file, (percent) => setProgress(percent));
        onUploaded(doc.id);
      } catch (err) {
        onError(errorMessage(err));
      } finally {
        setProgress(null);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [onUploaded, onError],
  );

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void handleFile(event.dataTransfer.files[0]);
  };

  return (
    <div>
      <div
        data-testid="drop-zone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? "border-slate-500 bg-slate-50" : "border-slate-300 hover:bg-slate-50"
        }`}
      >
        <p className="text-sm font-medium text-slate-700">
          Drop a contract here, or click to choose a file
        </p>
        <p className="text-xs text-slate-500">PDF or DOCX · up to 25 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => void handleFile(e.target.files?.[0])}
          data-testid="file-input"
        />
      </div>
      {validationError && (
        <p role="alert" data-testid="upload-validation-error" className="mt-2 text-sm text-red-600">
          {validationError}
        </p>
      )}
      {progress !== null && (
        <div className="mt-2" data-testid="upload-progress">
          <InlineSpinner label={`Uploading… ${progress}%`} />
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-slate-200">
            <div className="h-full bg-slate-700 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

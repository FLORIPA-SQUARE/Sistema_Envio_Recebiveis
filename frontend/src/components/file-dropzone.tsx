"use client";

import { useCallback, useState } from "react";
import { Upload, X, FileText, FileCode } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileDropzoneProps {
  accept: string;
  label: string;
  icon: "pdf" | "xml";
  files: File[];
  onFilesChange: (files: File[]) => void;
}

export function FileDropzone({
  accept,
  label,
  icon,
  files,
  onFilesChange,
}: FileDropzoneProps) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const exts = accept.split(",").map((a) => a.trim().toLowerCase());
      const droppedFiles = Array.from(e.dataTransfer.files).filter((f) =>
        exts.some((ext) => f.name.toLowerCase().endsWith(ext))
      );
      onFilesChange([...files, ...droppedFiles]);
    },
    [accept, files, onFilesChange]
  );

  const handleSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        onFilesChange([...files, ...Array.from(e.target.files)]);
      }
      e.target.value = "";
    },
    [files, onFilesChange]
  );

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  const Icon = icon === "pdf" ? FileText : FileCode;

  return (
    <div className="space-y-3">
      <div
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
        <p className="mb-1 text-sm font-medium">{label}</p>
        <p className="mb-3 text-xs text-muted-foreground">
          Arraste e solte ou clique para selecionar
        </p>
        <label>
          <input
            type="file"
            accept={accept}
            multiple
            className="hidden"
            onChange={handleSelect}
          />
          <span className="cursor-pointer rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            Selecionar arquivos
          </span>
        </label>
      </div>

      {files.length > 0 && (
        <div className="space-y-1">
          <p className="text-sm font-medium">
            {files.length} arquivo(s) selecionado(s)
          </p>
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${i}`}
                className="flex items-center gap-2 rounded-md bg-muted px-3 py-1.5 text-sm"
              >
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate flex-1">{file.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(0)} KB
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={() => removeFile(i)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

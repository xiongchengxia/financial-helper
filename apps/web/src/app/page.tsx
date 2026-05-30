"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { uploadTask } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File | null) {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const task = await uploadTask(file);
      router.push(`/tasks/${task.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>上传发票</h1>
      <div className="card upload-zone">
        <p>支持 JPG / PNG / WebP（≤10MB）或 PDF 发票（≤20MB，最多 10 页）</p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 16 }}>
          <label className="btn btn-primary">
            {loading ? "上传中…" : "选择文件"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf,.pdf"
              hidden
              disabled={loading}
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="btn">
            拍照上传
            <input
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              disabled={loading}
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        {error && <p style={{ color: "var(--danger)", marginTop: 12 }}>{error}</p>}
      </div>
    </main>
  );
}

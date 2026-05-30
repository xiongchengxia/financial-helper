"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { deleteDocument, fetchDocuments, type DocumentRecord } from "@/lib/api";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchDocuments()
      .then(setDocs)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(id: string, invoiceNumber: string) {
    const label = invoiceNumber || id.slice(0, 8);
    if (!window.confirm(`确定删除发票文档「${label}」？关联会计凭证将一并删除。`)) {
      return;
    }
    setDeletingId(id);
    setError(null);
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="container">
      <h1>发票文档</h1>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>类型</th>
              <th>发票号码</th>
              <th>置信度</th>
              <th>合规</th>
              <th>风险数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link href={`/documents/${d.id}`}>{d.kind}</Link>
                </td>
                <td>{String(d.payload.invoice_number ?? "—")}</td>
                <td>{(d.confidence * 100).toFixed(0)}%</td>
                <td>
                  {d.compliance ? (d.compliance.passed ? "通过" : "未通过") : "—"}
                </td>
                <td>{d.risks.length}</td>
                <td>
                  <button
                    type="button"
                    className="btn"
                    disabled={deletingId === d.id}
                    onClick={() =>
                      handleDelete(d.id, String(d.payload.invoice_number ?? ""))
                    }
                    style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
                  >
                    {deletingId === d.id ? "删除中…" : "删除"}
                  </button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr>
                <td colSpan={6}>暂无文档</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

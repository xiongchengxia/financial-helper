"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  deleteDocument,
  fetchDocument,
  fetchMedia,
  mediaUrl,
  type DocumentRecord,
} from "@/lib/api";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [isPdf, setIsPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const allRulesPassed =
    doc?.compliance?.hits.every((h) => h.passed) ?? false;
  const hasBlockRisk = doc?.risks.some((r) => r.level === "block") ?? false;

  useEffect(() => {
    fetchDocument(id)
      .then(async (d) => {
        setDoc(d);
        const media = await fetchMedia(d.mediaId);
        setIsPdf(media.mimeType === "application/pdf");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [id]);

  if (error) {
    return (
      <main className="container">
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  if (!doc) {
    return (
      <main className="container">
        <p>加载中…</p>
      </main>
    );
  }

  const p = doc.payload;

  async function handleDelete() {
    const num = String(p.invoice_number ?? id.slice(0, 8));
    if (!window.confirm(`确定删除发票「${num}」？关联凭证将一并删除。`)) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteDocument(id);
      router.push("/documents");
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
      setDeleting(false);
    }
  }

  return (
    <main className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <h1 style={{ margin: 0 }}>发票详情</h1>
        <button
          type="button"
          className="btn"
          disabled={deleting}
          onClick={handleDelete}
          style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
        >
          {deleting ? "删除中…" : "删除文档"}
        </button>
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>{isPdf ? "原始 PDF" : "原图"}</h2>
          {isPdf ? (
            <iframe
              src={mediaUrl(doc.mediaId)}
              title="发票 PDF"
              style={{ width: "100%", height: 480, border: "1px solid var(--border)", borderRadius: 8 }}
            />
          ) : (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={mediaUrl(doc.mediaId)}
              alt="发票原图"
              style={{ maxWidth: "100%", borderRadius: 8 }}
            />
          )}
        </div>
        <div className="card">
          <h2>结构化字段</h2>
          <ul>
            <li>代码：{String(p.invoice_code ?? "")}</li>
            <li>号码：{String(p.invoice_number ?? "")}</li>
            <li>开票日期：{String(p.issue_date ?? "")}</li>
            <li>购买方：{String(p.buyer_name ?? "")}</li>
            <li>销售方：{String(p.seller_name ?? "")}</li>
            <li>不含税：{String(p.amount_without_tax ?? "")}</li>
            <li>税额：{String(p.tax_amount ?? "")}</li>
            <li>价税合计：{String(p.total_with_tax ?? "")}</li>
          </ul>
          <p>置信度：{(doc.confidence * 100).toFixed(0)}%</p>
        </div>
      </div>

      {doc.compliance && (
        <div className="card">
          <h2>合规审核</h2>
          <p>
            整体结果：{doc.compliance.passed ? (
              <span style={{ color: "var(--ok)" }}>通过</span>
            ) : (
              <span style={{ color: "var(--danger)" }}>未通过</span>
            )}
          </p>
          {!doc.compliance.passed && allRulesPassed && hasBlockRisk && (
            <p style={{ color: "var(--muted)", fontSize: 14 }}>
              上方形式规则均已通过，但因存在 <strong>阻断级风险</strong>（见下方「风险标记」），整体合规判定为未通过。
              重复测试上传同一发票号码时会触发 <code>RISK_DUPLICATE</code>，删除旧文档后可重新测试。
            </p>
          )}
          <table>
            <thead>
              <tr>
                <th>规则</th>
                <th>通过</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {doc.compliance.hits.map((h) => (
                <tr key={h.ruleId}>
                  <td>{h.ruleId}</td>
                  <td>{h.passed ? "是" : "否"}</td>
                  <td>{h.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {doc.risks.length > 0 && (
        <div className="card">
          <h2>风险标记</h2>
          <ul>
            {doc.risks.map((r) => (
              <li key={r.code}>
                <span className={`badge badge-${r.level === "block" ? "block" : r.level === "warn" ? "warn" : "info"}`}>
                  {r.level}
                </span>{" "}
                <strong>{r.code}</strong> — {r.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}

"use client";

import { exportVouchersUrl } from "@/lib/api";

export default function ExportPage() {
  return (
    <main className="container">
      <h1>导出凭证</h1>
      <div className="card">
        <p>导出当前库中全部会计凭证（可按日期筛选请使用 API 查询参数）。</p>
        <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
          <a className="btn btn-primary" href={exportVouchersUrl("xlsx")} download>
            下载 Excel
          </a>
          <a className="btn" href={exportVouchersUrl("json")} target="_blank" rel="noreferrer">
            查看 JSON
          </a>
        </div>
        <p style={{ marginTop: 16, color: "var(--muted)", fontSize: 14 }}>
          Excel 含三张表：凭证主表、分录明细、风险明细。
        </p>
      </div>
    </main>
  );
}

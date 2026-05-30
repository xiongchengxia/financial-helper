"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchVoucher, type VoucherRecord } from "@/lib/api";

export default function VoucherDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [voucher, setVoucher] = useState<VoucherRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVoucher(id)
      .then(setVoucher)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [id]);

  if (error) {
    return (
      <main className="container">
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  if (!voucher) {
    return (
      <main className="container">
        <p>加载中…</p>
      </main>
    );
  }

  return (
    <main className="container">
      <h1>
        凭证 {voucher.voucherWord}-{voucher.voucherNo}
      </h1>
      <div className="card">
        <p>日期：{voucher.voucherDate}</p>
        <p>业务类型：{voucher.eventType}</p>
        <p>
          借贷合计：借 {voucher.debitTotal.toFixed(2)} / 贷 {voucher.creditTotal.toFixed(2)}
        </p>
        <table>
          <thead>
            <tr>
              <th>行</th>
              <th>科目编码</th>
              <th>科目名称</th>
              <th>借方</th>
              <th>贷方</th>
              <th>摘要</th>
            </tr>
          </thead>
          <tbody>
            {voucher.lines.map((l) => (
              <tr key={l.lineNo}>
                <td>{l.lineNo}</td>
                <td>{l.accountCode}</td>
                <td>{l.accountName}</td>
                <td>{l.debit > 0 ? l.debit.toFixed(2) : ""}</td>
                <td>{l.credit > 0 ? l.credit.toFixed(2) : ""}</td>
                <td>{l.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchVouchers, type VoucherRecord } from "@/lib/api";

export default function VouchersPage() {
  const [vouchers, setVouchers] = useState<VoucherRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVouchers()
      .then(setVouchers)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, []);

  return (
    <main className="container">
      <h1>会计凭证</h1>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>凭证号</th>
              <th>日期</th>
              <th>借方合计</th>
              <th>贷方合计</th>
              <th>来源文档</th>
            </tr>
          </thead>
          <tbody>
            {vouchers.map((v) => (
              <tr key={v.id}>
                <td>
                  <Link href={`/vouchers/${v.id}`}>
                    {v.voucherWord}-{v.voucherNo}
                  </Link>
                </td>
                <td>{v.voucherDate}</td>
                <td>{v.debitTotal.toFixed(2)}</td>
                <td>{v.creditTotal.toFixed(2)}</td>
                <td>
                  {v.documentIds[0] ? (
                    <Link href={`/documents/${v.documentIds[0]}`}>查看</Link>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
            {vouchers.length === 0 && (
              <tr>
                <td colSpan={5}>暂无凭证</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

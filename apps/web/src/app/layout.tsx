import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "财税票据助手",
  description: "发票识别、合规审核与会计凭证导出",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <nav className="nav">
          <Link href="/">上传</Link>
          <Link href="/tasks">任务</Link>
          <Link href="/documents">发票</Link>
          <Link href="/vouchers">凭证</Link>
          <Link href="/export">导出</Link>
        </nav>
        {children}
        <div className="container">
          <p className="disclaimer">
            本系统输出仅供参考，入账与纳税申报责任由企业/会计人员承担。请以主管税务机关要求为准。
          </p>
        </div>
      </body>
    </html>
  );
}

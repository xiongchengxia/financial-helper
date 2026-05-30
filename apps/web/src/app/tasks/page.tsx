"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchTasks, type RecognitionTask } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<RecognitionTask[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks()
      .then(setTasks)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, []);

  return (
    <main className="container">
      <h1>识别任务</h1>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>任务 ID</th>
              <th>状态</th>
              <th>文档</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>
                  <Link href={`/tasks/${t.id}`}>{t.id.slice(0, 8)}…</Link>
                </td>
                <td>
                  <StatusBadge status={t.status} />
                </td>
                <td>
                  {t.documentId ? (
                    <Link href={`/documents/${t.documentId}`}>查看</Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{t.createdAt}</td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={4}>暂无任务</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

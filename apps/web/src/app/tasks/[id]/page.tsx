"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchTask, type RecognitionTask } from "@/lib/api";

export default function TaskDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const [task, setTask] = useState<RecognitionTask | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const t = await fetchTask(id);
        if (cancelled) return;
        setTask(t);
        if (t.status === "completed" && t.documentId) {
          router.replace(`/documents/${t.documentId}`);
          return;
        }
        if (t.status === "pending" || t.status === "processing") {
          setTimeout(poll, 4000);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  if (error) {
    return (
      <main className="container">
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  if (!task) {
    return (
      <main className="container">
        <p>加载中…</p>
      </main>
    );
  }

  return (
    <main className="container">
      <h1>任务详情</h1>
      <div className="card">
        <p>
          状态：<span className={`badge badge-${task.status}`}>{task.status}</span>
        </p>
        {task.errorMessage && (
          <p style={{ color: "var(--danger)" }}>错误：{task.errorMessage}</p>
        )}
        {task.durationMs != null && <p>耗时：{task.durationMs} ms</p>}
        {task.status === "failed" && (
          <p>
            <Link href="/">重新上传</Link>
          </p>
        )}
        {(task.status === "pending" || task.status === "processing") && (
          <p>识别处理中，请稍候（约每 4 秒刷新）…</p>
        )}
      </div>
    </main>
  );
}

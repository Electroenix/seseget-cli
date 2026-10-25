import { useCallback, useEffect, useState } from "react";
import type {
  DownloadHistoryData,
  DownloadHistoryItem,
  DownloadTask,
} from "../types/api";
import { clearDownloadHistory, fetchDownloadHistory } from "../api/client";
import DownloadListPanel from "./DownloadListPanel";

interface DownloadPageProps {
  tasks: DownloadTask[];
  historyVersion: number;
}

type DownloadTab = "active" | "history";

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  success: { label: "成功", className: "text-bg-success" },
  failed: { label: "失败", className: "text-bg-danger" },
  cancelled: { label: "已取消", className: "text-bg-secondary" },
};

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "-";
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)} 秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes < 60) {
    return `${minutes} 分 ${rest} 秒`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours} 小时 ${minutes % 60} 分`;
}

function HistoryRow({ item }: { item: DownloadHistoryItem }) {
  const status = STATUS_CONFIG[item.status] ?? {
    label: item.status,
    className: "text-bg-secondary",
  };

  return (
    <tr>
      <td style={{ minWidth: "180px", maxWidth: "360px" }}>
        <div className="text-truncate" title={item.name}>
          {item.name}
        </div>
      </td>
      <td>
        <span className={`badge ${status.className}`}>{status.label}</span>
      </td>
      <td className="text-nowrap small text-muted">
        {formatTime(item.finished_at)}
      </td>
      <td className="text-nowrap small text-muted">
        {formatDuration(item.duration)}
      </td>
      <td className="text-nowrap small text-muted">
        {item.file_finish_count}/{item.file_count}
      </td>
      <td style={{ minWidth: "160px", maxWidth: "320px" }}>
        {item.error ? (
          <span className="small text-danger text-truncate d-inline-block" title={item.error}>
            {item.error}
          </span>
        ) : (
          <span className="text-muted">-</span>
        )}
      </td>
    </tr>
  );
}

export default function DownloadPage({
  tasks,
  historyVersion,
}: DownloadPageProps) {
  const [tab, setTab] = useState<DownloadTab>("active");
  const [history, setHistory] = useState<DownloadHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadHistory = async () => {
      try {
        const response = await fetchDownloadHistory();
        if (cancelled) return;
        if (response.code !== 200 || !response.data) {
          throw new Error(response.message || "加载下载历史失败");
        }
        setError("");
        setHistory(response.data);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load download history:", err);
          setError("加载下载历史失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [historyVersion]);

  const handleClearHistory = useCallback(async () => {
    if (clearing) return;
    if (!window.confirm("确定清空全部下载历史吗？此操作不可撤销。")) {
      return;
    }

    setClearing(true);
    setError("");
    try {
      const response = await clearDownloadHistory();
      if (response.code !== 200) {
        throw new Error(response.message || "清空下载历史失败");
      }
      setHistory((prev) => ({
        items: [],
        total: 0,
        max_items: prev?.max_items ?? 200,
      }));
    } catch (err) {
      console.error("Failed to clear download history:", err);
      setError("清空下载历史失败");
    } finally {
      setClearing(false);
    }
  }, [clearing]);

  const historyCount = history?.total ?? 0;

  return (
    <div className="container py-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h4 className="mb-1">下载管理</h4>
          <div className="text-muted small">
            查看正在进行的下载和已结束的历史任务
          </div>
        </div>
        <div className="text-muted small">
          历史最多保留 {history?.max_items ?? 200} 条
        </div>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link ${tab === "active" ? "active" : ""}`}
            onClick={() => setTab("active")}
          >
            <i className="bi bi-download me-1" />
            正在下载
            <span className="badge bg-secondary ms-2">{tasks.length}</span>
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link ${tab === "history" ? "active" : ""}`}
            onClick={() => setTab("history")}
          >
            <i className="bi bi-clock-history me-1" />
            下载历史
            <span className="badge bg-secondary ms-2">{historyCount}</span>
          </button>
        </li>
      </ul>

      {error && (
        <div className="alert alert-danger py-2" role="alert">
          {error}
        </div>
      )}

      {tab === "active" ? (
        <DownloadListPanel tasks={tasks} title="正在下载" />
      ) : (
        <div className="card">
          <div className="card-header py-2 d-flex flex-wrap justify-content-between align-items-center gap-2">
            <span className="fw-semibold">
              下载历史
              <span className="text-muted small ms-2">
                共 {historyCount} 条
              </span>
            </span>
            <button
              type="button"
              className="btn btn-outline-danger btn-sm"
              onClick={handleClearHistory}
              disabled={clearing || historyCount === 0}
            >
              {clearing ? "清空中..." : "清空历史"}
            </button>
          </div>

          {loading ? (
            <div className="text-center text-muted py-4">
              <span className="spinner-border spinner-border-sm me-2" />
              加载中...
            </div>
          ) : history && history.items.length > 0 ? (
            <div className="table-responsive">
              <table className="table table-sm table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>任务</th>
                    <th>状态</th>
                    <th>完成时间</th>
                    <th>耗时</th>
                    <th>文件</th>
                    <th>错误</th>
                  </tr>
                </thead>
                <tbody>
                  {history.items.map((item) => (
                    <HistoryRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-muted py-4">
              <i className="bi bi-inbox" style={{ fontSize: "1.5rem" }} />
              <div className="mt-1">暂无下载历史</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Clock3,
  Download,
  Inbox,
  ListChecks,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import type {
  DownloadHistoryData,
  DownloadHistoryItem,
  DownloadTask,
  SiteOption,
} from "../types/api";
import { clearDownloadHistory, fetchDownloadHistory } from "../api/client";
import { Button, EmptyState, Panel, StatusPill } from "../components/ui";
import { cx } from "../lib/cx";

interface DownloadsPageProps {
  tasks: DownloadTask[];
  historyVersion: number;
  siteList: SiteOption[];
}

type DownloadTab = "active" | "history";

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const decimals = unit === 0 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(decimals)} ${units[unit]}`;
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "-";
  if (seconds < 60) return `${seconds.toFixed(1)} 秒`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes < 60) return `${minutes} 分 ${rest} 秒`;
  const hours = Math.floor(minutes / 60);
  return `${hours} 小时 ${minutes % 60} 分`;
}

function HistoryRow({
  item,
  siteList,
}: {
  item: DownloadHistoryItem;
  siteList: SiteOption[];
}) {
  const siteName = siteList.find((site) => site.key === item.site)?.name ?? item.site ?? "-";
  const tone =
    item.status === "success" ? "success" : item.status === "failed" ? "danger" : "neutral";
  const label =
    item.status === "success"
      ? "成功"
      : item.status === "failed"
        ? "失败"
        : item.status === "cancelled"
          ? "已取消"
          : item.status;

  return (
    <tr className="border-b border-edge-soft last:border-0">
      <td className="max-w-[320px] px-4 py-3">
        <div className="truncate text-xs text-fg" title={item.name}>
          {item.name}
        </div>
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-[11px] text-muted">
        {siteName}
      </td>
      <td className="px-4 py-3">
        <StatusPill tone={tone}>{label}</StatusPill>
      </td>
      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
        {formatBytes(item.total_bytes)}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-[11px] text-muted">
        {formatTime(item.finished_at)}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-[11px] text-muted">
        {formatDuration(item.duration)}
      </td>
      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-muted">
        {item.file_finish_count}/{item.file_count}
      </td>
      <td className="max-w-[240px] px-4 py-3">
        {item.error ? (
          <span className="block truncate text-[11px] text-danger" title={item.error}>
            {item.error}
          </span>
        ) : (
          <span className="text-[11px] text-faint">-</span>
        )}
      </td>
    </tr>
  );
}

export default function DownloadsPage({
  tasks,
  historyVersion,
  siteList,
}: DownloadsPageProps) {
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
        if (!cancelled) setLoading(false);
      }
    };

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [historyVersion]);

  const handleClearHistory = useCallback(async () => {
    if (clearing) return;
    if (!window.confirm("确定清空全部下载历史吗？此操作不可撤销。")) return;

    setClearing(true);
    setError("");
    try {
      const response = await clearDownloadHistory();
      if (response.code !== 200) throw new Error(response.message || "清空下载历史失败");
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

  const tabButton = (value: DownloadTab, label: string, count: number, icon: ReactNode) => (
    <button
      type="button"
      onClick={() => setTab(value)}
      className={cx(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition",
        tab === value
          ? "bg-raised text-fg shadow-[inset_0_-2px_0_var(--color-accent)]"
          : "text-muted hover:bg-white/5 hover:text-fg",
      )}
    >
      {icon}
      {label}
      <span className="rounded-full border border-edge bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-faint">
        {count}
      </span>
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1 rounded-xl border border-edge bg-panel p-1">
          {tabButton("active", "运行中", tasks.length, <Download className="h-3.5 w-3.5" />)}
          {tabButton("history", "历史记录", historyCount, <Clock3 className="h-3.5 w-3.5" />)}
        </div>
        <div className="text-[11px] text-faint">
          历史最多保留 {history?.max_items ?? 200} 条
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger">
          {error}
        </div>
      )}

      {tab === "active" ? (
        <Panel className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-medium text-fg">
              <ListChecks className="h-4 w-4 text-accent" />
              任务队列
            </div>
            <span className="font-mono text-[10px] text-faint">{tasks.length} 项</span>
          </div>

          {tasks.length === 0 ? (
            <EmptyState
              icon={<Inbox className="h-5 w-5" />}
              title="暂无运行中的任务"
              description="从媒体解析页面选择章节并开始下载后，任务会显示在这里。"
            />
          ) : (
            <div className="divide-y divide-edge-soft">
              {tasks.map((task) => {
                const failed = task.status === "ERR";
                const done = task.status === "OK";
                return (
                  <div key={task.id} className="px-4 py-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <div className="min-w-0 truncate text-xs text-fg" title={task.name}>
                          {task.name}
                        </div>
                        <span className="shrink-0 rounded border border-edge bg-raised px-1.5 py-0.5 text-[10px] text-faint">
                          {siteList.find((site) => site.key === task.site)?.name ?? task.site ?? "-"}
                        </span>
                      </div>
                      <StatusPill tone={failed ? "danger" : done ? "success" : "neutral"}>
                        {failed ? "失败" : done ? "完成" : `${task.progress.toFixed(1)}%`}
                      </StatusPill>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
                        <div
                          className={cx(
                            "h-full rounded-full transition-all",
                            failed ? "bg-danger" : done ? "bg-success" : "bg-accent",
                          )}
                          style={{ width: `${Math.min(100, Math.max(0, task.progress))}%` }}
                        />
                      </div>
                      <span className="w-16 shrink-0 text-right font-mono text-[10px] text-faint">
                        {task.file_finish_count}/{task.file_count}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>
      ) : (
        <Panel className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-medium text-fg">
              <Clock3 className="h-4 w-4 text-accent" />
              下载历史
              <span className="font-mono text-[10px] font-normal text-faint">{historyCount} 条</span>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={handleClearHistory}
              disabled={clearing || historyCount === 0}
            >
              {clearing ? (
                <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              {clearing ? "清空中..." : "清空历史"}
            </Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              加载中...
            </div>
          ) : history && history.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-edge text-[10px] uppercase tracking-wider text-faint">
                    <th className="px-4 py-2.5 font-medium">任务</th>
                    <th className="px-4 py-2.5 font-medium">站点</th>
                    <th className="px-4 py-2.5 font-medium">状态</th>
                    <th className="px-4 py-2.5 font-medium">总大小</th>
                    <th className="px-4 py-2.5 font-medium">完成时间</th>
                    <th className="px-4 py-2.5 font-medium">耗时</th>
                    <th className="px-4 py-2.5 font-medium">文件</th>
                    <th className="px-4 py-2.5 font-medium">错误</th>
                  </tr>
                </thead>
                <tbody>
                  {history.items.map((item) => (
                    <HistoryRow key={item.id} item={item} siteList={siteList} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={<Inbox className="h-5 w-5" />}
              title="暂无下载历史"
              description="已完成或失败的下载任务会记录在这里。"
            />
          )}
        </Panel>
      )}
    </div>
  );
}

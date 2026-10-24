import type { DownloadTask } from "../types/api";

interface DownloadListPanelProps {
  tasks: DownloadTask[];
  title?: string;
  emptyText?: string;
}

export default function DownloadListPanel({
  tasks,
  title = "正在下载",
  emptyText = "暂无正在下载的任务",
}: DownloadListPanelProps) {
  return (
    <div className="download-list-panel card">
      <div className="card-header py-2 d-flex justify-content-between align-items-center">
        <span className="fw-semibold">{title}</span>
        <span className="badge bg-secondary">{tasks.length}</span>
      </div>
      <div
        className="list-group list-group-flush"
        style={{ maxHeight: "60vh", overflowY: "auto" }}
      >
        {tasks.length === 0 ? (
          <div className="list-group-item text-center text-muted py-4">
            <i className="bi bi-inbox" style={{ fontSize: "1.5rem" }} />
            <div className="mt-1">{emptyText}</div>
          </div>
        ) : (
          tasks.map((task) => (
            <div className="list-group-item" key={task.id}>
              <div className="text-truncate small mb-2">{task.name}</div>
              <div className="d-flex align-items-center gap-2">
                <div className="flex-grow-1">
                  <div
                    className="progress"
                    role="progressbar"
                    style={{ height: "6px" }}
                  >
                    <div
                      className="progress-bar bg-primary"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                </div>
                <div className="d-flex gap-2 text-nowrap" style={{ width: "130px", flexShrink: 0 }}>
                  <span className="text-muted small">
                    [{task.file_finish_count}/{task.file_count}]
                  </span>
                  <span
                    className={`small ${
                      task.status === "ERR"
                        ? "text-danger"
                        : task.status === "OK"
                          ? "text-success"
                          : "text-muted"
                    }`}
                  >
                    {task.status === "ERR"
                      ? "失败"
                      : task.status === "OK"
                        ? "OK"
                        : task.progress.toFixed(1) + "%"}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

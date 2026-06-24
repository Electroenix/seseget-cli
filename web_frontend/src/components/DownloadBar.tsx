interface DownloadBarProps {
  showCheckboxes: boolean;
  onToggleBatch: () => void;
  onSelectAll: (checked: boolean) => void;
  onDownloadSelected: () => void;
}

export default function DownloadBar({
  showCheckboxes,
  onToggleBatch,
  onSelectAll,
  onDownloadSelected,
}: DownloadBarProps) {
  return (
    <div>
      <div className="batch-bar">
        <button
          className="btn btn-outline-primary btn-sm"
          onClick={onToggleBatch}
        >
          <i className="bi bi-list-check me-1" />
          批量选择
        </button>
      </div>
      {showCheckboxes && (
        <div className="select-bar">
          <div className="d-flex align-items-center gap-2">
            <input
              type="checkbox"
              className="form-check-input m-0"
              id="selectAllCb"
              onChange={(e) => onSelectAll(e.target.checked)}
            />
            <label className="form-check-label small" htmlFor="selectAllCb">
              全选
            </label>
          </div>
          <div className="d-flex gap-2">
            <button
              className="btn btn-primary btn-sm"
              onClick={onDownloadSelected}
            >
              <i className="bi bi-download me-1" />
              下载选中
            </button>
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={onToggleBatch}
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

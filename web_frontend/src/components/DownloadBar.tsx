import { Download, ListChecks, X } from "lucide-react";
import { Button } from "./ui";

interface DownloadBarProps {
  showCheckboxes: boolean;
  selectedCount: number;
  totalChapters: number;
  onToggleBatch: () => void;
  onSelectAll: (checked: boolean) => void;
  onDownloadSelected: () => void;
}

export default function DownloadBar({
  showCheckboxes,
  selectedCount,
  totalChapters,
  onToggleBatch,
  onSelectAll,
  onDownloadSelected,
}: DownloadBarProps) {
  if (!showCheckboxes) {
    return (
      <Button variant="secondary" size="sm" onClick={onToggleBatch}>
        <ListChecks className="h-3.5 w-3.5" />
        批量选择
      </Button>
    );
  }

  const allSelected = totalChapters > 0 && selectedCount === totalChapters;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
        <input
          type="checkbox"
          className="h-4 w-4 accent-accent"
          checked={allSelected}
          onChange={(event) => onSelectAll(event.target.checked)}
        />
        全选
      </label>
      <Button
        variant="primary"
        size="sm"
        onClick={onDownloadSelected}
        disabled={selectedCount === 0}
      >
        <Download className="h-3.5 w-3.5" />
        下载选中 {selectedCount > 0 && `(${selectedCount})`}
      </Button>
      <Button variant="ghost" size="sm" onClick={onToggleBatch}>
        <X className="h-3.5 w-3.5" />
        取消
      </Button>
    </div>
  );
}

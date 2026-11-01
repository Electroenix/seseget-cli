import { Download, ExternalLink } from "lucide-react";
import type { Chapter } from "../types/api";
import { Button } from "./ui";

interface ChapterPanelProps {
  chapters: Chapter[];
  showCheckboxes: boolean;
  selectedChapters: Set<number>;
  onToggleChapter: (order: number) => void;
  onJump: (station: string, url: string) => void;
  onDownloadSingle: (station: string, url: string, chapterOrder: number) => void;
  station: string;
}

export default function ChapterPanel({
  chapters,
  showCheckboxes,
  selectedChapters,
  onToggleChapter,
  onJump,
  onDownloadSingle,
  station,
}: ChapterPanelProps) {
  if (chapters.length === 0) {
    return <div className="px-5 py-8 text-center text-xs text-muted">没有可下载的章节</div>;
  }

  return (
    <div className="max-h-[440px] divide-y divide-edge-soft overflow-y-auto">
      {chapters.map((chapter) => (
        <div
          key={chapter.order}
          className="flex items-center gap-3 px-5 py-3 transition hover:bg-white/[0.025]"
        >
          {showCheckboxes && (
            <input
              type="checkbox"
              className="h-4 w-4 shrink-0 accent-accent"
              checked={selectedChapters.has(chapter.order)}
              onChange={() => onToggleChapter(chapter.order)}
              aria-label={`选择第 ${chapter.order} 章`}
            />
          )}

          {chapter.thumbnail ? (
            <img
              src={chapter.thumbnail}
              alt=""
              className="h-11 w-20 shrink-0 rounded-md border border-edge object-cover"
            />
          ) : (
            <div className="flex h-11 w-20 shrink-0 items-center justify-center rounded-md border border-edge bg-raised text-[10px] text-faint">
              NO IMAGE
            </div>
          )}

          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-fg" title={chapter.title}>
              {chapter.title}
            </div>
            <div className="mt-0.5 text-[11px] text-faint">
              第 {chapter.order} 项
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onJump(station, chapter.url)}
              title="跳转解析"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">跳转</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onDownloadSingle(station, chapter.url, chapter.order)}
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">下载</span>
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

import type { ReactNode } from "react";
import { CalendarDays, Layers3, Tags, UserRound } from "lucide-react";
import type { MediaInfo } from "../types/api";
import ChapterPanel from "./ChapterPanel";
import DownloadBar from "./DownloadBar";
import { Panel } from "./ui";

interface InfoPanelProps {
  info: MediaInfo;
  showCheckboxes: boolean;
  selectedChapters: Set<number>;
  onSeriesClick: (station: string, url: string) => void;
  onJump: (station: string, url: string) => void;
  onDownloadSingle: (station: string, url: string, chapterOrder: number) => void;
  onToggleBatch: () => void;
  onSelectAll: (checked: boolean) => void;
  onDownloadSelected: () => void;
  onToggleChapter: (order: number) => void;
}

function MetaRow({
  icon,
  label,
  children,
}: {
  icon: ReactNode;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 items-start gap-2 text-xs">
      <span className="mt-0.5 text-faint">{icon}</span>
      <span className="w-10 shrink-0 text-faint">{label}</span>
      <span className="min-w-0 flex-1 break-words text-muted">{children}</span>
    </div>
  );
}

export default function InfoPanel({
  info,
  showCheckboxes,
  selectedChapters,
  onSeriesClick,
  onJump,
  onDownloadSingle,
  onToggleBatch,
  onSelectAll,
  onDownloadSelected,
  onToggleChapter,
}: InfoPanelProps) {
  const genres = info.genres ?? [];

  return (
    <Panel className="overflow-hidden">
      <div className="grid gap-6 p-5 lg:grid-cols-[210px_minmax(0,1fr)]">
        <div className="mx-auto w-full max-w-[210px] lg:mx-0">
          {info.cover ? (
            <img
              src={info.cover}
              alt={info.title}
              className="aspect-[3/4] w-full rounded-lg border border-edge object-cover"
            />
          ) : (
            <div className="flex aspect-[3/4] w-full items-center justify-center rounded-lg border border-edge bg-raised text-xs text-faint">
              暂无封面
            </div>
          )}
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-semibold leading-7 text-fg">{info.title}</h2>
              {info.sub_title && <p className="mt-1 text-xs text-muted">{info.sub_title}</p>}
            </div>
            <span className="rounded-md border border-edge bg-raised px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-faint">
              {info.station}
            </span>
          </div>

          <div className="mt-4 grid gap-2.5">
            {info.author && (
              <MetaRow icon={<UserRound className="h-3.5 w-3.5" />} label="作者">
                {info.author}
              </MetaRow>
            )}
            {info.date && (
              <MetaRow icon={<CalendarDays className="h-3.5 w-3.5" />} label="日期">
                {info.date}
              </MetaRow>
            )}
            {info.series && (
              <MetaRow icon={<Layers3 className="h-3.5 w-3.5" />} label="系列">
                <button
                  type="button"
                  className="text-left text-accent transition hover:text-accent-hover hover:underline"
                  onClick={() => onSeriesClick(info.station, info.url)}
                >
                  {info.series}
                </button>
              </MetaRow>
            )}
          </div>

          {genres.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-1.5">
              <Tags className="mr-1 h-3.5 w-3.5 text-faint" />
              {genres.map((genre) => (
                <span
                  key={genre}
                  className="rounded-md border border-edge bg-raised px-2 py-0.5 text-[11px] text-muted"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {info.description && (
            <p className="mt-4 max-h-28 overflow-y-auto whitespace-pre-line text-xs leading-5 text-muted">
              {info.description}
            </p>
          )}
        </div>
      </div>

      <div className="border-t border-edge">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">章节</h3>
            <span className="rounded-full border border-edge bg-raised px-2 py-0.5 text-[10px] text-muted">
              {info.chapter.length}
            </span>
          </div>
          <DownloadBar
            showCheckboxes={showCheckboxes}
            selectedCount={selectedChapters.size}
            totalChapters={info.chapter.length}
            onToggleBatch={onToggleBatch}
            onSelectAll={onSelectAll}
            onDownloadSelected={onDownloadSelected}
          />
        </div>
        <ChapterPanel
          station={info.station}
          chapters={info.chapter}
          showCheckboxes={showCheckboxes}
          selectedChapters={selectedChapters}
          onToggleChapter={onToggleChapter}
          onJump={onJump}
          onDownloadSingle={onDownloadSingle}
        />
      </div>
    </Panel>
  );
}

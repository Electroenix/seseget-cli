import { Search } from "lucide-react";
import type { MediaInfo, SiteOption } from "../types/api";
import InfoPanel from "../components/InfoPanel";
import SearchBar from "../components/SearchBar";
import { EmptyState, Panel } from "../components/ui";

interface SearchPageProps {
  siteList: SiteOption[];
  station: string;
  url: string;
  onStationChange: (station: string) => void;
  onUrlChange: (url: string) => void;
  mediaInfo: MediaInfo | null;
  searchError: string;
  showCheckboxes: boolean;
  selectedChapters: Set<number>;
  onSearch: (formData: FormData) => void;
  onSeriesClick: (station: string, url: string) => void;
  onJump: (station: string, url: string) => void;
  onDownloadSingle: (station: string, url: string, chapterOrder: number) => void;
  onToggleBatch: () => void;
  onSelectAll: (checked: boolean) => void;
  onDownloadSelected: () => void;
  onToggleChapter: (order: number) => void;
}

export default function SearchPage({
  siteList,
  station,
  url,
  onStationChange,
  onUrlChange,
  mediaInfo,
  searchError,
  showCheckboxes,
  selectedChapters,
  onSearch,
  onSeriesClick,
  onJump,
  onDownloadSingle,
  onToggleBatch,
  onSelectAll,
  onDownloadSelected,
  onToggleChapter,
}: SearchPageProps) {
  return (
    <div className="space-y-4">
      <SearchBar
        siteList={siteList}
        station={station}
        url={url}
        onStationChange={onStationChange}
        onUrlChange={onUrlChange}
        onSubmit={onSearch}
      />

      {searchError && (
        <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-xs text-danger">
          {searchError}
        </div>
      )}

      {mediaInfo ? (
        <InfoPanel
          info={mediaInfo}
          showCheckboxes={showCheckboxes}
          selectedChapters={selectedChapters}
          onSeriesClick={onSeriesClick}
          onJump={onJump}
          onDownloadSingle={onDownloadSingle}
          onToggleBatch={onToggleBatch}
          onSelectAll={onSelectAll}
          onDownloadSelected={onDownloadSelected}
          onToggleChapter={onToggleChapter}
        />
      ) : (
        <Panel>
          <EmptyState
            icon={<Search className="h-5 w-5" />}
            title="粘贴链接开始解析"
            description="选择站点后输入作品链接。解析后可查看信息并下载所需章节。"
            action={
              <div className="flex max-w-lg flex-wrap justify-center gap-1.5">
                {siteList.map((site) => (
                  <span
                    key={site.key}
                    className="rounded-md border border-edge bg-raised px-2 py-1 text-[11px] text-muted"
                  >
                    {site.name}
                  </span>
                ))}
              </div>
            }
          />
        </Panel>
      )}
    </div>
  );
}

import type { MediaInfo } from "../types/api";
import DownloadBar from "./DownloadBar";
import ChapterPanel from "./ChapterPanel";

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
  return (
    <div className="info-panel">
      {/* Cover + Metadata row */}
      <div className="row mb-3">
        <div className="col-md-4 col-lg-3 mb-3 mb-md-0">
          <img
            className="cover-image"
            src={info.cover}
            alt={info.title}
          />
        </div>
        <div className="metadata-panel col-md-8 col-lg-9">
          {info.title && <h1 className="mb-2">{info.title}</h1>}

          {info.sub_title && (
            <div className="meta-row">
              <span>{info.sub_title}</span>
            </div>
          )}

          {info.date && (
            <div className="meta-row">
              <span className="meta-label">日期:</span>
              <span>{info.date}</span>
            </div>
          )}

          {info.series && (
            <div className="meta-row">
              <span className="meta-label">系列:</span>
              <button
                className="series-btn btn btn-link btn-sm p-0"
                onClick={() => onSeriesClick(info.station, info.url)}
              >
                {info.series}
              </button>
            </div>
          )}

          {info.author && (
            <div className="meta-row">
              <span className="meta-label">作者:</span>
              <span>{info.author}</span>
            </div>
          )}

          {info.genres && info.genres.length > 0 && (
            <div className="mt-2">
              {info.genres.map((genre) => (
                <span className="tag" key={genre}>
                  {genre}
                </span>
              ))}
            </div>
          )}

          {info.description && (
            <p className="description-text mt-2">{info.description}</p>
          )}
        </div>
      </div>

      <hr />

      {/* Download bar (batch) */}
      <DownloadBar
        showCheckboxes={showCheckboxes}
        onToggleBatch={onToggleBatch}
        onSelectAll={onSelectAll}
        onDownloadSelected={onDownloadSelected}
      />

      {/* Chapter list */}
      <ChapterPanel
        station={info.station}
        url={info.url}
        chapters={info.chapter}
        showCheckboxes={showCheckboxes}
        selectedChapters={selectedChapters}
        onToggleChapter={onToggleChapter}
        onJump={onJump}
        onDownloadSingle={onDownloadSingle}
      />
    </div>
  );
}

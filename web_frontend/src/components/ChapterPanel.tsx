import type { Chapter } from "../types/api";

interface ChapterPanelProps {
  station: string;
  url: string;
  chapters: Chapter[];
  showCheckboxes: boolean;
  selectedChapters: Set<number>;
  onToggleChapter: (order: number) => void;
  onJump: (station: string, url: string) => void;
  onDownloadSingle: (station: string, url: string, chapterOrder: number) => void;
}

export default function ChapterPanel({
  station,
  chapters,
  showCheckboxes,
  selectedChapters,
  onToggleChapter,
  onJump,
  onDownloadSingle,
}: ChapterPanelProps) {
  return (
    <div className="chapter-box">
      <ul className="list-group">
        {chapters.map((chapter) => (
          <li className="list-group-item" key={chapter.order}>
            <div className="chapter-list-item">
              {/* Checkbox */}
              {showCheckboxes && (
                <input
                  type="checkbox"
                  className="form-check-input m-0 flex-shrink-0"
                  checked={selectedChapters.has(chapter.order)}
                  onChange={() => onToggleChapter(chapter.order)}
                />
              )}

              {/* Thumbnail */}
              {chapter.thumbnail && chapter.thumbnail !== "" && (
                <img
                  className="chapter-thumb"
                  src={chapter.thumbnail}
                  alt=""
                />
              )}

              {/* Title */}
              <span className="chapter-title-text">{chapter.title}</span>

              {/* Actions */}
              <div className="chapter-actions">
                <button
                  className="btn btn-sm btn-outline-secondary"
                  onClick={() => onJump(station, chapter.url)}
                >
                  <i className="bi bi-box-arrow-up-right me-1" />
                  跳转
                </button>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() =>
                    onDownloadSingle(station, chapter.url, chapter.order)
                  }
                >
                  <i className="bi bi-download me-1" />
                  下载
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

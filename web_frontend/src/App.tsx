import { useState, useEffect, useCallback } from "react";
import type { MediaInfo, DownloadTask, ConfigObject } from "./types/api";
import {
  fetchSiteList,
  fetchSearch,
  fetchSeriesInfo,
  downloadMedia,
  fetchSettings,
  saveSettings,
  fetchWebSettings,
  saveWebSettings,
} from "./api/client";
import { useDownloadSocket } from "./hooks/useSocket";
import { useAuth } from "./contexts/AuthContext";
import LoginPage from "./components/LoginPage";
import NavBar from "./components/NavBar";
import SearchBar from "./components/SearchBar";
import InfoPanel from "./components/InfoPanel";
import ConfigPanel from "./components/ConfigPanel";

export default function App() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <MainApp />;
}

function MainApp() {
  // Search / site state
  const [siteList, setSiteList] = useState<string[]>([]);
  const [mediaInfo, setMediaInfo] = useState<MediaInfo | null>(null);

  // Batch download state
  const [showCheckboxes, setShowCheckboxes] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());

  // Download list via WebSocket
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  useDownloadSocket(setDownloadTasks);

  // Config modal state
  const [configOpen, setConfigOpen] = useState(false);
  const [configData, setConfigData] = useState<ConfigObject | null>(null);
  const [webConfigData, setWebConfigData] = useState<ConfigObject | null>(null);
  const [configKey, setConfigKey] = useState(0);

  // Load site list on mount
  useEffect(() => {
    fetchSiteList()
      .then((res) => setSiteList(res.data ?? []))
      .catch(console.error);
  }, []);

  // --- Search handlers ---
  const handleSearch = useCallback(async (formData: FormData) => {
    try {
      const res = await fetchSearch(formData);
      if (res.data) {
        setMediaInfo(res.data);
        setShowCheckboxes(false);
        setSelectedChapters(new Set());
      }
    } catch (err) {
      console.error("Search error:", err);
    }
  }, []);

  const handleChapterJump = useCallback(
    async (station: string, url: string) => {
      const formData = new FormData();
      formData.append("station", station);
      formData.append("url", url);
      await handleSearch(formData);
    },
    [handleSearch]
  );

  const handleSeriesClick = useCallback(
    async (station: string, url: string) => {
      try {
        const res = await fetchSeriesInfo(station, url);
        if (res.data) {
          setMediaInfo(res.data);
          setShowCheckboxes(false);
          setSelectedChapters(new Set());
        }
      } catch (err) {
        console.error("Series fetch error:", err);
      }
    },
    []
  );

  // --- Download handlers ---
  const handleDownloadSingle = useCallback(
    async (station: string, url: string, chapterOrder: number) => {
      try {
        await downloadMedia(station, url, [chapterOrder]);
      } catch (err) {
        console.error("Download error:", err);
      }
    },
    []
  );

  const handleDownloadSelected = useCallback(async () => {
    if (!mediaInfo || selectedChapters.size === 0) return;

    const station = mediaInfo.station;
    let url: string;
    let chapters: (string | number)[];

    try {
      if (station === "hanime") {
        // Hanime: 每个视频 URL 不同，传入chapters列表中
        url = "";
        chapters = mediaInfo.chapter
          .filter((ch) => selectedChapters.has(ch.order))
          .map((ch) => ch.url);
      } else {
        // 其他站点: 同一 URL，传章节 ID 列表
        url = mediaInfo.url;
        chapters = Array.from(selectedChapters);
      }

      await downloadMedia(station, url, chapters);
    } catch (err) {
      console.error("Batch download error:", err);
    }
  }, [mediaInfo, selectedChapters]);

  // --- Batch toggle handlers ---
  const handleToggleBatch = useCallback(() => {
    setShowCheckboxes((prev) => {
      if (prev) {
        // Hiding - clear selections
        setSelectedChapters(new Set());
      }
      return !prev;
    });
  }, []);

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (!mediaInfo) return;
      if (checked) {
        setSelectedChapters(
          new Set(mediaInfo.chapter.map((ch) => ch.order))
        );
      } else {
        setSelectedChapters(new Set());
      }
    },
    [mediaInfo]
  );

  const handleToggleChapter = useCallback((order: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(order)) {
        next.delete(order);
      } else {
        next.add(order);
      }
      return next;
    });
  }, []);

  // --- Config handlers ---
  const handleOpenConfig = useCallback(async () => {
    try {
      const [mainRes, webRes] = await Promise.all([
        fetchSettings(),
        fetchWebSettings(),
      ]);
      setConfigData(mainRes.data as ConfigObject);
      setWebConfigData(webRes.data as ConfigObject);
      setConfigKey((k) => k + 1);
      setConfigOpen(true);
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  }, []);

  const handleCloseConfig = useCallback(() => {
    setConfigOpen(false);
  }, []);

  const handleSaveConfig = useCallback(async (config: ConfigObject) => {
    try {
      await saveSettings(config);
      setConfigOpen(false);
    } catch (err) {
      console.error("Failed to save config:", err);
    }
  }, []);

  const handleSaveWebConfig = useCallback(async (config: ConfigObject) => {
    try {
      await saveWebSettings(config);
      setConfigOpen(false);
    } catch (err) {
      console.error("Failed to save web config:", err);
    }
  }, []);

  return (
    <>
      <NavBar
        downloadTasks={downloadTasks}
        onOpenConfig={handleOpenConfig}
      />

      <div className="container-fluid">
        <div className="row justify-content-center">
          <div className="col-lg-6">
            <SearchBar siteList={siteList} onSubmit={handleSearch} />

            {mediaInfo && (
              <InfoPanel
                info={mediaInfo}
                showCheckboxes={showCheckboxes}
                selectedChapters={selectedChapters}
                onSeriesClick={handleSeriesClick}
                onJump={handleChapterJump}
                onDownloadSingle={handleDownloadSingle}
                onToggleBatch={handleToggleBatch}
                onSelectAll={handleSelectAll}
                onDownloadSelected={handleDownloadSelected}
                onToggleChapter={handleToggleChapter}
              />
            )}
          </div>
        </div>
      </div>

      {configOpen && (
        <ConfigPanel
          key={configKey}
          open={configOpen}
          config={configData}
          webConfig={webConfigData}
          onSave={handleSaveConfig}
          onSaveWeb={handleSaveWebConfig}
          onClose={handleCloseConfig}
        />
      )}
    </>
  );
}

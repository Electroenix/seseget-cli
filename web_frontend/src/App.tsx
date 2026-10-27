import { useState, useEffect, useCallback } from "react";
import type {
  MediaInfo,
  DownloadTask,
  ConfigObject,
  ConfigChanges,
  ConfigSchema,
  FormatOptions,
} from "./types/api";
import {
  fetchSiteList,
  fetchSearch,
  fetchSeriesInfo,
  downloadMedia,
  fetchSettings,
  fetchConfigSchema,
  fetchFormatOptions,
  saveSettings,
  fetchWebSettings,
  saveWebSettings,
  fetchVersion,
} from "./api/client";
import { useDownloadSocket } from "./hooks/useSocket";
import { useAuth } from "./contexts/AuthContext";
import type { MainPage } from "./types/ui";
import LoginPage from "./components/LoginPage";
import NavBar from "./components/NavBar";
import SearchBar from "./components/SearchBar";
import InfoPanel from "./components/InfoPanel";
import ConfigPage from "./components/ConfigPage";
import DownloadPage from "./components/DownloadPage";

const VIDEO_STATIONS = new Set(["hanime", "bilibili", "youtube", "twitter"]);

export default function App() {
  const { isAuthenticated } = useAuth();
  const [version, setVersion] = useState<string>("");

  useEffect(() => {
    fetchVersion()
      .then((res) => setVersion(res.data?.version ?? ""))
      .catch(console.error);
  }, []);

  if (!isAuthenticated) {
    return <LoginPage version={version} />;
  }

  return <MainApp version={version} />;
}

function MainApp({ version }: { version: string }) {
  // Search / site state
  const [siteList, setSiteList] = useState<string[]>([]);
  const [mediaInfo, setMediaInfo] = useState<MediaInfo | null>(null);

  // Main page navigation, ready to extend to settings later
  const [activePage, setActivePage] = useState<MainPage>("search");

  // Batch download state
  const [showCheckboxes, setShowCheckboxes] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());

  // Download list via WebSocket
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  const [historyVersion, setHistoryVersion] = useState(0);
  const handleDownloadFinished = useCallback(() => {
    setHistoryVersion((version) => version + 1);
  }, []);
  useDownloadSocket(setDownloadTasks, handleDownloadFinished);

  // Config page state
  const [configData, setConfigData] = useState<ConfigObject | null>(null);
  const [webConfigData, setWebConfigData] = useState<ConfigObject | null>(null);
  const [webSecretConfigured, setWebSecretConfigured] = useState<string[]>([]);
  const [secretFields, setSecretFields] = useState<string[]>([]);
  const [secretConfigured, setSecretConfigured] = useState<string[]>([]);
  const [configSchema, setConfigSchema] = useState<ConfigSchema | null>(null);
  const [formatOptions, setFormatOptions] = useState<FormatOptions | null>(null);

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
      if (VIDEO_STATIONS.has(station)) {
        // 视频站点：每集/每个视频的 URL 不同，传 URL 列表
        url = "";
        chapters = mediaInfo.chapter
          .filter((ch) => selectedChapters.has(ch.order))
          .map((ch) => ch.url);
      } else {
        // 漫画站点：同一作品 URL，传章节 ID 列表
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
  const loadConfig = useCallback(async () => {
    try {
      const formatsPromise = fetchFormatOptions().catch((err) => {
        console.error("Failed to load format options:", err);
        return null;
      });
      const schemaPromise = fetchConfigSchema().catch((err) => {
        console.error("Failed to load config schema:", err);
        return null;
      });
      const [mainRes, webRes, formatsRes, schemaRes] = await Promise.all([
        fetchSettings(),
        fetchWebSettings(),
        formatsPromise,
        schemaPromise,
      ]);
      setConfigData(mainRes.data.config);
      setSecretFields(mainRes.data.secret_fields);
      setSecretConfigured(mainRes.data.secret_configured);
      setConfigSchema(schemaRes?.data ?? null);
      setWebConfigData(webRes.data.config);
      setWebSecretConfigured(webRes.data.secret_configured);
      setFormatOptions(formatsRes?.data ?? null);
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  }, []);

  const handleSaveConfig = useCallback(async (changes: ConfigChanges) => {
    try {
      const response = await saveSettings(changes);
      if (response.code !== 200) {
        window.alert(response.message || "保存配置失败");
        return false;
      }
      return true;
    } catch (err) {
      console.error("Failed to save config:", err);
      return false;
    }
  }, []);

  const handleSaveWebConfig = useCallback(async (changes: ConfigChanges) => {
    try {
      const response = await saveWebSettings(changes);
      if (response.code !== 200) {
        window.alert(response.message || "保存 Web 配置失败");
        return false;
      }
      return true;
    } catch (err) {
      console.error("Failed to save web config:", err);
      return false;
    }
  }, []);

  const handleNavigate = useCallback(
    (page: MainPage) => {
      if (page !== "settings") {
        setActivePage(page);
        return;
      }
      void loadConfig().then(() => setActivePage("settings"));
    },
    [loadConfig]
  );

  return (
    <>
      <NavBar
        activePage={activePage}
        onNavigate={handleNavigate}
        downloadTasks={downloadTasks}
        version={version}
      />

      {activePage === "settings" ? (
        <ConfigPage
          config={configData}
          webConfig={webConfigData}
          schema={configSchema}
          formatOptions={formatOptions}
          secretFields={secretFields}
          secretConfigured={secretConfigured}
          webConfigured={webSecretConfigured.includes("auth_token")}
          onSave={handleSaveConfig}
          onSaveWeb={handleSaveWebConfig}
        />
      ) : activePage === "download" ? (
        <DownloadPage
          tasks={downloadTasks}
          historyVersion={historyVersion}
        />
      ) : (
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
      )}

    </>
  );
}

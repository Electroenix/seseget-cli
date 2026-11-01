import { useCallback, useEffect, useState } from "react";
import { fetchVersion } from "./api/client";
import AppShell from "./components/AppShell";
import ConfigPage from "./components/ConfigPage";
import LoginPage from "./components/LoginPage";
import { useAuth } from "./contexts/AuthContext";
import { useConfigSettings } from "./hooks/useConfigSettings";
import { useDownloadTasks } from "./hooks/useDownloadTasks";
import { useMediaSearch } from "./hooks/useMediaSearch";
import { useSearchForm } from "./hooks/useSearchForm";
import { useSiteList } from "./hooks/useSiteList";
import DownloadsPage from "./pages/DownloadsPage";
import SearchPage from "./pages/SearchPage";
import type { MainPage } from "./types/ui";

export default function App() {
  const { isAuthenticated } = useAuth();
  const [version, setVersion] = useState("");

  useEffect(() => {
    fetchVersion()
      .then((response) => setVersion(response.data?.version ?? ""))
      .catch(console.error);
  }, []);

  if (!isAuthenticated) {
    return <LoginPage version={version} />;
  }

  return <MainApp version={version} />;
}

function MainApp({ version }: { version: string }) {
  const [page, setPage] = useState<MainPage>("search");
  const { siteList, error: siteError } = useSiteList();
  const searchForm = useSearchForm(siteList);
  const search = useMediaSearch();
  const config = useConfigSettings();
  const downloads = useDownloadTasks();
  const loadConfig = config.load;

  const navigate = useCallback(
    async (next: MainPage) => {
      if (next === "settings") {
        await loadConfig();
      }
      setPage(next);
    },
    [loadConfig],
  );

  return (
    <AppShell
      page={page}
      version={version}
      activeDownloads={downloads.tasks.length}
      onNavigate={navigate}
    >
      {page === "settings" ? (
        <ConfigPage
          config={config.data}
          schema={config.schema}
          formatOptions={config.formatOptions}
          secretFields={config.secretFields}
          secretConfigured={config.secretConfigured}
          onSave={config.save}
        />
      ) : page === "download" ? (
        <DownloadsPage
          tasks={downloads.tasks}
          historyVersion={downloads.historyVersion}
          siteList={siteList}
        />
      ) : (
        <SearchPage
          siteList={siteList}
          station={searchForm.station}
          url={searchForm.url}
          onStationChange={searchForm.setStation}
          onUrlChange={searchForm.setUrl}
          mediaInfo={search.mediaInfo}
          searchError={search.searchError || siteError}
          showCheckboxes={search.showCheckboxes}
          selectedChapters={search.selectedChapters}
          onSearch={search.search}
          onSeriesClick={search.openSeries}
          onJump={search.jump}
          onDownloadSingle={search.downloadSingle}
          onToggleBatch={search.toggleBatch}
          onSelectAll={search.selectAll}
          onDownloadSelected={search.downloadSelected}
          onToggleChapter={search.toggleChapter}
        />
      )}
    </AppShell>
  );
}

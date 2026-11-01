import { useCallback, useState } from "react";
import type { MediaInfo } from "../types/api";
import { downloadMedia, fetchSearch, fetchSeriesInfo } from "../api/client";

const VIDEO_STATIONS = new Set(["hanime", "bilibili", "youtube", "twitter"]);

export function useMediaSearch() {
  const [mediaInfo, setMediaInfo] = useState<MediaInfo | null>(null);
  const [searchError, setSearchError] = useState("");
  const [showCheckboxes, setShowCheckboxes] = useState(false);
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());

  const applyResult = useCallback((info: MediaInfo) => {
    setMediaInfo(info);
    setShowCheckboxes(false);
    setSelectedChapters(new Set());
  }, []);

  const search = useCallback(async (formData: FormData) => {
    setSearchError("");
    try {
      const response = await fetchSearch(formData);
      if (response.code !== 200) {
        setSearchError(response.message || "搜索失败");
        return;
      }
      if (response.data) applyResult(response.data);
    } catch (err) {
      console.error("Search error:", err);
      setSearchError(err instanceof Error ? err.message : "搜索失败");
    }
  }, [applyResult]);

  const jump = useCallback(async (station: string, url: string) => {
    const formData = new FormData();
    formData.append("station", station);
    formData.append("url", url);
    await search(formData);
  }, [search]);

  const openSeries = useCallback(async (station: string, url: string) => {
    try {
      const response = await fetchSeriesInfo(station, url);
      if (response.code !== 200) {
        setSearchError(response.message || "系列信息获取失败");
        return;
      }
      if (response.data) applyResult(response.data);
    } catch (err) {
      console.error("Series fetch error:", err);
      setSearchError(err instanceof Error ? err.message : "系列信息获取失败");
    }
  }, [applyResult]);

  const downloadSingle = useCallback(async (station: string, url: string, chapterOrder: number) => {
    try {
      await downloadMedia(station, url, [chapterOrder]);
    } catch (err) {
      console.error("Download error:", err);
    }
  }, []);

  const downloadSelected = useCallback(async () => {
    if (!mediaInfo || selectedChapters.size === 0) return;

    const station = mediaInfo.station;
    let url: string;
    let chapters: (string | number)[];

    try {
      if (VIDEO_STATIONS.has(station)) {
        url = "";
        chapters = mediaInfo.chapter
          .filter((chapter) => selectedChapters.has(chapter.order))
          .map((chapter) => chapter.url);
      } else {
        url = mediaInfo.url;
        chapters = Array.from(selectedChapters);
      }
      await downloadMedia(station, url, chapters);
    } catch (err) {
      console.error("Batch download error:", err);
    }
  }, [mediaInfo, selectedChapters]);

  const toggleBatch = useCallback(() => {
    setShowCheckboxes((prev) => {
      if (prev) setSelectedChapters(new Set());
      return !prev;
    });
  }, []);

  const selectAll = useCallback((checked: boolean) => {
    if (!mediaInfo) return;
    setSelectedChapters(
      checked ? new Set(mediaInfo.chapter.map((chapter) => chapter.order)) : new Set(),
    );
  }, [mediaInfo]);

  const toggleChapter = useCallback((order: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(order)) next.delete(order);
      else next.add(order);
      return next;
    });
  }, []);

  return {
    mediaInfo,
    searchError,
    showCheckboxes,
    selectedChapters,
    search,
    jump,
    openSeries,
    downloadSingle,
    downloadSelected,
    toggleBatch,
    selectAll,
    toggleChapter,
  };
}

import { useEffect, useState } from "react";
import type { SiteOption } from "../types/api";
import { fetchSiteList } from "../api/client";

export function useSiteList() {
  const [siteList, setSiteList] = useState<SiteOption[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    fetchSiteList()
      .then((response) => {
        if (cancelled) return;
        setSiteList(response.data ?? []);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load sites:", err);
        setError("站点列表加载失败");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { siteList, error };
}

import { useState } from "react";
import type { SiteOption } from "../types/api";

export function useSearchForm(siteList: SiteOption[]) {
  const [station, setStation] = useState("");
  const [url, setUrl] = useState("");

  const selectedStation = siteList.some((site) => site.key === station)
    ? station
    : (siteList[0]?.key ?? "");

  return { station: selectedStation, url, setStation, setUrl };
}

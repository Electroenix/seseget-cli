import type { FormEvent } from "react";
import { Globe2, Link2, Search } from "lucide-react";
import type { SiteOption } from "../types/api";
import { Button } from "./ui";

interface SearchBarProps {
  siteList: SiteOption[];
  station: string;
  url: string;
  onStationChange: (station: string) => void;
  onUrlChange: (url: string) => void;
  onSubmit: (formData: FormData) => void;
}

export default function SearchBar({
  siteList,
  station,
  url,
  onStationChange,
  onUrlChange,
  onSubmit,
}: SearchBarProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(new FormData(event.currentTarget));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="panel flex flex-col gap-2 p-2 sm:flex-row sm:items-center"
    >
      <div className="relative sm:w-40">
        <Globe2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <select
          className="field appearance-none pl-9"
          name="station"
          value={station}
          onChange={(event) => onStationChange(event.target.value)}
          aria-label="选择站点"
        >
          {siteList.map((site) => (
            <option key={site.key} value={site.key}>
              {site.name}
            </option>
          ))}
        </select>
      </div>
      <div className="relative min-w-0 flex-1">
        <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <input
          className="field pl-9 font-mono text-xs"
          type="text"
          name="url"
          placeholder="粘贴作品链接..."
          value={url}
          onChange={(event) => onUrlChange(event.target.value)}
          autoComplete="off"
          spellCheck={false}
          aria-label="媒体链接"
        />
      </div>
      <Button type="submit" variant="primary" className="shrink-0 sm:px-5">
        <Search className="h-4 w-4" />
        获取信息
      </Button>
    </form>
  );
}

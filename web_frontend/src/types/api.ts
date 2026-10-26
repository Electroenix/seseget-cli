// --- API Response Envelope ---
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// --- Chapter ---
export interface Chapter {
  title: string;
  url: string;
  thumbnail: string;
  order: number;
}

// --- Search Result (InfoPanel data) ---
export interface MediaInfo {
  station: string;
  url: string;
  title: string;
  sub_title: string;
  date: string;
  series: string;
  author: string;
  genres: string[];
  description: string;
  cover: string;
  chapter: Chapter[];
}

// --- Download Task ---
export interface DownloadTask {
  id: string;
  name: string;
  progress: number;
  speed: number;
  status: string;
  file_count: number;
  file_finish_count: number;
}

// --- Download History ---
export interface DownloadHistoryItem {
  id: string;
  name: string;
  status: "success" | "failed" | "cancelled" | string;
  started_at: string;
  finished_at: string;
  duration: number;
  file_count: number;
  file_finish_count: number;
  progress: number;
  error: string;
}

export interface DownloadHistoryData {
  items: DownloadHistoryItem[];
  total: number;
  max_items: number;
}

// --- Config (recursive, any shape) ---
export type ConfigValue = string | number | boolean | string[] | ConfigObject;
export interface ConfigObject {
  [key: string]: ConfigValue;
}

export interface ConfigSettingsData {
  config: ConfigObject;
  secret_fields: string[];
  secret_configured: string[];
}

export type ConfigFieldKind = "str" | "bool" | "int" | "str_list" | string;

export interface ConfigFieldSchema {
  label: string;
  description: string;
  kind: ConfigFieldKind;
  secret: boolean;
  editable: boolean;
}

export interface ConfigSectionSchema {
  label: string;
  description: string;
}

export interface ConfigSchema {
  sections: Record<string, ConfigSectionSchema>;
  fields: Record<string, ConfigFieldSchema>;
}

export type ConfigChanges = Record<string, unknown>;

// --- Config field options (field path -> available formats) ---
export type FormatOptions = Record<string, string[]>;

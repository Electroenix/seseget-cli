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
  name: string;
  progress: number;
  speed: number;
  status: string;
  file_count: number;
  file_finish_count: number;
}

// --- Config (recursive, any shape) ---
export type ConfigValue = string | number | boolean | ConfigObject;
export interface ConfigObject {
  [key: string]: ConfigValue;
}

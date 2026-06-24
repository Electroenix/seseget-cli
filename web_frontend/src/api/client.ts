import type { ApiResponse, MediaInfo, ConfigObject } from "../types/api";

const TOKEN_KEY = "seseget_auth_token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  if (response.status === 401) {
    // Token 失效，清除本地存储
    localStorage.removeItem(TOKEN_KEY);
    window.location.reload();
    throw new Error("Authentication required");
  }
  return response.json();
}

// GET /api/search/site_list
export async function fetchSiteList(): Promise<ApiResponse<string[]>> {
  const response = await fetch("/api/search/site_list", {
    method: "GET",
    headers: authHeaders(),
  });
  return handleResponse<string[]>(response);
}

// POST /api/search  (FormData: station, url)
export async function fetchSearch(formData: FormData): Promise<ApiResponse<MediaInfo>> {
  const response = await fetch("/api/search", {
    method: "POST",
    body: formData,
    headers: authHeaders(),
  });
  return handleResponse<MediaInfo>(response);
}

// POST /api/search/series  (JSON: station, url)
export async function fetchSeriesInfo(
  station: string,
  url: string
): Promise<ApiResponse<MediaInfo>> {
  const response = await fetch("/api/search/series", {
    method: "POST",
    body: JSON.stringify({ station, url }),
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse<MediaInfo>(response);
}

// POST /api/download  (JSON: station, url, chapters)
export async function downloadMedia(
  station: string,
  url: string,
  chapters: (string | number)[]
): Promise<ApiResponse> {
  const response = await fetch("/api/download", {
    method: "POST",
    body: JSON.stringify({ station, url, chapters }),
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse(response);
}

// GET /api/settings
export async function fetchSettings(): Promise<ApiResponse<ConfigObject>> {
  const response = await fetch("/api/settings", {
    method: "GET",
    headers: authHeaders(),
  });
  return handleResponse<ConfigObject>(response);
}

// POST /api/settings/save
export async function saveSettings(config: ConfigObject): Promise<ApiResponse> {
  const response = await fetch("/api/settings/save", {
    method: "POST",
    body: JSON.stringify(config),
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse(response);
}

// GET /api/web-settings
export async function fetchWebSettings(): Promise<ApiResponse<ConfigObject>> {
  const response = await fetch("/api/web-settings", {
    method: "GET",
    headers: authHeaders(),
  });
  return handleResponse<ConfigObject>(response);
}

// POST /api/web-settings/save
export async function saveWebSettings(config: ConfigObject): Promise<ApiResponse> {
  const response = await fetch("/api/web-settings/save", {
    method: "POST",
    body: JSON.stringify(config),
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse(response);
}

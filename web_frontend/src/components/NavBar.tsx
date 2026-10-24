import type { DownloadTask } from "../types/api";
import type { MainPage } from "../types/ui";
import { useAuth } from "../contexts/AuthContext";

interface NavBarProps {
  activePage: MainPage;
  onNavigate: (page: MainPage) => void;
  downloadTasks: DownloadTask[];
  onOpenConfig: () => void;
  version: string;
}

export default function NavBar({
  activePage,
  onNavigate,
  downloadTasks,
  onOpenConfig,
  version,
}: NavBarProps) {
  const { logout } = useAuth();

  return (
    <nav className="navbar navbar-expand bg-body-tertiary fixed-top border-bottom">
      <div className="container-fluid">
        <a
          className="logo"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            onNavigate("search");
          }}
        >
          seseGet{" "}
          {version && (
            <span className="badge bg-secondary fw-normal" style={{ fontSize: "0.65rem", verticalAlign: "text-top" }}>
              v{version}
            </span>
          )}
        </a>
        <ul className="navbar-nav ms-auto">
          <li className="nav-item me-2">
            <a
              className={`nav-link ${activePage === "search" ? "active" : ""}`}
              href="#"
              role="button"
              aria-current={activePage === "search" ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                onNavigate("search");
              }}
            >
              <i className="bi bi-search me-1" />
              搜索
            </a>
          </li>
          <li className="nav-item me-2">
            <a
              className={`nav-link ${activePage === "download" ? "active" : ""}`}
              href="#"
              role="button"
              aria-current={activePage === "download" ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                onNavigate("download");
              }}
            >
              <i className="bi bi-download me-1" />
              下载
              {downloadTasks.length > 0 && (
                <span className="badge bg-secondary ms-1">
                  {downloadTasks.length}
                </span>
              )}
            </a>
          </li>
          <li className="nav-item me-2">
            <a className="nav-link" href="#" role="button" onClick={(e) => { e.preventDefault(); onOpenConfig(); }}>
              <i className="bi bi-gear me-1" />
              配置
            </a>
          </li>
          <li className="nav-item">
            <a
              className="nav-link text-muted"
              href="#"
              role="button"
              title="退出登录"
              onClick={(e) => { e.preventDefault(); logout(); }}
            >
              <i className="bi bi-box-arrow-right" />
            </a>
          </li>
        </ul>
      </div>
    </nav>
  );
}

import type { DownloadTask } from "../types/api";
import { useAuth } from "../contexts/AuthContext";
import DownloadListPanel from "./DownloadListPanel";

interface NavBarProps {
  downloadTasks: DownloadTask[];
  onOpenConfig: () => void;
}

export default function NavBar({
  downloadTasks,
  onOpenConfig,
}: NavBarProps) {
  const { logout } = useAuth();

  return (
    <nav className="navbar navbar-expand bg-body-tertiary fixed-top border-bottom">
      <div className="container-fluid">
        <a className="logo" href="#">
          seseGet
        </a>
        <ul className="navbar-nav ms-auto">
          <li className="nav-item dropdown me-2">
            <a
              className="nav-link dropdown-toggle"
              href="#"
              role="button"
              data-bs-toggle="dropdown"
              data-bs-auto-close="outside"
              aria-expanded="false"
            >
              <i className="bi bi-download me-1" />
              下载列表
            </a>
            <div className="dropdown-menu dropdown-menu-end p-0">
              <DownloadListPanel tasks={downloadTasks} />
            </div>
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

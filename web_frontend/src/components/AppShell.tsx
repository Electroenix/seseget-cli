import { useState, type ReactNode } from "react";
import {
  BookOpen,
  Download,
  Library,
  LogOut,
  Menu,
  Search,
  Settings,
  X,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import type { MainPage } from "../types/ui";
import { cx } from "../lib/cx";

interface AppShellProps {
  page: MainPage;
  version: string;
  activeDownloads: number;
  onNavigate: (page: MainPage) => void;
  children: ReactNode;
}

const NAV_ITEMS = [
  { page: "search" as const, label: "搜索", icon: Search },
  { page: "download" as const, label: "下载任务", icon: Download },
  { page: "settings" as const, label: "设置", icon: Settings },
];

const PAGE_META: Record<MainPage, { title: string; description: string }> = {
  search: { title: "媒体解析", description: "获取作品信息并选择需要下载的内容" },
  download: { title: "下载任务", description: "查看进行中的任务和下载历史" },
  settings: { title: "设置", description: "管理站点、网络和输出选项" },
};

function SidebarContent({
  page,
  version,
  activeDownloads,
  onNavigate,
  onLogout,
}: {
  page: MainPage;
  version: string;
  activeDownloads: number;
  onNavigate: (page: MainPage) => void;
  onLogout: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-edge px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <Library className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[18px] font-semibold leading-none tracking-tight text-fg">
              seseGet
            </span>
            {version && (
              <span className="rounded border border-edge bg-raised px-1.5 py-0.5 font-mono text-[11px] leading-none text-muted">
                v{version}
              </span>
            )}
          </div>
          <div className="mt-1 text-[9px] uppercase tracking-[0.16em] text-faint">
            Download Workbench
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-faint">
          工作区
        </div>
        {NAV_ITEMS.map(({ page: itemPage, label, icon: Icon }) => (
          <button
            key={itemPage}
            type="button"
            onClick={() => onNavigate(itemPage)}
            className={cx(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
              page === itemPage
                ? "bg-accent-soft text-fg shadow-[inset_2px_0_0_var(--color-accent)]"
                : "text-muted hover:bg-white/5 hover:text-fg",
            )}
          >
            <Icon className={cx("h-4 w-4", page === itemPage && "text-accent")} />
            <span className="flex-1 text-left">{label}</span>
            {itemPage === "download" && activeDownloads > 0 && (
              <span className="rounded-full border border-edge bg-raised px-2 py-0.5 text-[10px] text-muted">
                {activeDownloads}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="space-y-1 border-t border-edge p-3">
        <a
          href="https://github.com/Electroenix/seseget-cli#readme"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-white/5 hover:text-fg"
        >
          <BookOpen className="h-4 w-4" />
          项目文档
        </a>
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-white/5 hover:text-fg"
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </button>
      </div>
    </div>
  );
}

export default function AppShell({
  page,
  version,
  activeDownloads,
  onNavigate,
  children,
}: AppShellProps) {
  const { logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const meta = PAGE_META[page];

  const navigate = (next: MainPage) => {
    setMobileOpen(false);
    onNavigate(next);
  };

  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-edge bg-sidebar lg:block">
        <SidebarContent
          page={page}
          version={version}
          activeDownloads={activeDownloads}
          onNavigate={navigate}
          onLogout={logout}
        />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="关闭导航"
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-edge bg-sidebar">
            <button
              type="button"
              aria-label="关闭导航"
              className="icon-btn absolute right-3 top-3"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent
              page={page}
              version={version}
              activeDownloads={activeDownloads}
              onNavigate={navigate}
              onLogout={logout}
            />
          </aside>
        </div>
      )}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-edge bg-canvas/90 px-4 backdrop-blur sm:px-6">
          <button
            type="button"
            aria-label="打开导航"
            className="icon-btn lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-fg">{meta.title}</h1>
            <p className="truncate text-xs text-muted">{meta.description}</p>
          </div>
          {activeDownloads > 0 && (
            <div className="hidden items-center gap-2 rounded-lg border border-edge bg-panel px-3 py-1.5 text-xs sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              <span className="text-muted">{activeDownloads} 个任务进行中</span>
            </div>
          )}
        </header>

        <main className="mx-auto max-w-[1400px] p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}

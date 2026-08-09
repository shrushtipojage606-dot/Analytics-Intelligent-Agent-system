import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, UploadCloud, FileBarChart2, BellRing, Radar, LogOut } from "lucide-react";

interface SidebarProps {
  datasetId?: string;
}

export function Sidebar({ datasetId }: SidebarProps) {
  const { pathname } = useLocation();

  const items = [
    { label: "Upload Data", to: "/", icon: UploadCloud, match: (p: string) => p === "/" },
    {
      label: "Dashboard",
      to: datasetId ? `/dashboard/${datasetId}` : "/",
      icon: LayoutDashboard,
      match: (p: string) => p.startsWith("/dashboard"),
    },
    { label: "Reports", to: "/reports", icon: FileBarChart2, match: (p: string) => p.startsWith("/reports") },
    {
      label: "Email Alerts",
      to: datasetId ? `/alerts/${datasetId}` : "/alerts",
      icon: BellRing,
      match: (p: string) => p.startsWith("/alerts"),
    },
  ];

  return (
    <aside className="sticky top-0 flex h-screen w-56 flex-none flex-col border-r border-line bg-ink-900/60 px-3 py-5">
      <Link to="/" className="mb-8 flex items-center gap-2 px-2">
        <Radar className="text-signal-teal" size={20} />
        <span className="font-display text-sm font-semibold leading-tight text-mist-100">
          Analytics
          <br />
          Intelligence Agent
        </span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {items.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              to={item.to}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-signal-teal/10 text-signal-teal"
                  : "text-mist-500 hover:bg-ink-850 hover:text-mist-200"
              }`}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-line pt-4">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-signal-teal/15 font-mono-data text-xs text-signal-teal">
            AI
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-mist-200">Demo User</p>
            <p className="truncate text-[10px] text-mist-600">demo@analytics-agent.ai</p>
          </div>
          <button className="text-mist-600 hover:text-mist-300" title="Log out">
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}

import { getCurrentWindow } from "@tauri-apps/api/window";

interface Props {
  title?: string;
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

function TitlebarControls() {
  const win = getCurrentWindow();

  return (
    <div className="flex h-full shrink-0">
      <button
        onClick={() => win.minimize()}
        aria-label="Minimizar"
        className="flex h-full w-[46px] items-center justify-center text-[var(--app-text-muted)] hover:bg-black/[0.06] active:bg-black/[0.10]"
      >
        <svg width="10" height="1" viewBox="0 0 10 1" fill="currentColor">
          <rect width="10" height="1" />
        </svg>
      </button>
      <button
        onClick={() => win.toggleMaximize()}
        aria-label="Maximizar"
        className="flex h-full w-[46px] items-center justify-center text-[var(--app-text-muted)] hover:bg-black/[0.06] active:bg-black/[0.10]"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1">
          <rect x="0.5" y="0.5" width="9" height="9" />
        </svg>
      </button>
      <button
        onClick={() => win.close()}
        aria-label="Cerrar"
        className="flex h-full w-[46px] items-center justify-center text-[var(--app-text-muted)] hover:bg-[#c42b1c] hover:text-white active:bg-[#b22418]"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1">
          <line x1="0" y1="0" x2="10" y2="10" />
          <line x1="10" y1="0" x2="0" y2="10" />
        </svg>
      </button>
    </div>
  );
}

export function WindowsLayout({ title = "Actualización de Proveedores", sidebar, children }: Props) {
  return (
    <div
      className="flex h-screen flex-col"
      style={{ background: "var(--app-bg)" }}
    >
      {/* Custom titlebar */}
      <div
        className="app-titlebar flex shrink-0 items-center justify-between"
        data-tauri-drag-region
        style={{
          height: "var(--app-titlebar-height)",
          background: "var(--app-titlebar-bg)",
          borderBottom: "1px solid var(--app-border)",
        }}
      >
        <div
          className="flex flex-1 items-center gap-2 pl-3"
          data-tauri-drag-region
        >
          <span className="text-xs font-medium" style={{ color: "var(--app-text-muted)" }}>
            {title}
          </span>
        </div>
        <TitlebarControls />
      </div>

      {/* Body: sidebar + content */}
      <div className="flex flex-1 overflow-hidden">
        <aside
          className="ap-scrollbar flex shrink-0 flex-col overflow-y-auto"
          style={{
            width: "var(--app-sidebar-width)",
            background: "var(--app-sidebar-bg)",
            borderRight: "1px solid var(--app-border)",
          }}
        >
          {sidebar}
        </aside>

        <main
          className="ap-scrollbar flex-1 overflow-y-auto p-6"
          style={{ background: "var(--app-bg)" }}
        >
          <div style={{ maxWidth: "var(--app-content-max-w)", margin: "0 auto" }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

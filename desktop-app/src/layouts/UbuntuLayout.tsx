import { getCurrentWindow } from "@tauri-apps/api/window";

interface Props {
  title?: string;
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

function HeaderbarControls({ title }: { title: string }) {
  const win = getCurrentWindow();

  return (
    <>
      {/* GTK-style: controls on the LEFT */}
      <div className="flex items-center gap-1.5 pl-3 pr-2 shrink-0">
        <button
          onClick={() => win.close()}
          aria-label="Cerrar"
          className="flex h-[14px] w-[14px] items-center justify-center rounded-full bg-[#cc5c55] hover:bg-[#e0534a] active:bg-[#b84b45]"
        />
        <button
          onClick={() => win.minimize()}
          aria-label="Minimizar"
          className="flex h-[14px] w-[14px] items-center justify-center rounded-full bg-[#c4a240] hover:bg-[#d4af45] active:bg-[#b0913a]"
        />
        <button
          onClick={() => win.toggleMaximize()}
          aria-label="Maximizar"
          className="flex h-[14px] w-[14px] items-center justify-center rounded-full bg-[#58a65c] hover:bg-[#5cb860] active:bg-[#4e9451]"
        />
      </div>

      {/* Centered title */}
      <span
        className="pointer-events-none absolute left-1/2 -translate-x-1/2 text-sm font-semibold"
        style={{ color: "var(--app-text)" }}
        data-tauri-drag-region
      >
        {title}
      </span>
    </>
  );
}

export function UbuntuLayout({ title = "Actualización de Proveedores", sidebar, children }: Props) {
  return (
    <div
      className="flex h-screen flex-col"
      style={{ background: "var(--app-bg)" }}
    >
      {/* GNOME-style headerbar */}
      <header
        className="app-titlebar relative flex shrink-0 items-center"
        data-tauri-drag-region
        style={{
          height: "var(--app-titlebar-height)",
          background: "var(--app-titlebar-bg)",
          borderBottom: "1px solid var(--app-border-strong)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        <HeaderbarControls title={title} />
      </header>

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

export type Platform = "windows" | "ubuntu";

/** Sync detection from navigator.userAgent — used before async OS plugin resolves. */
function detectFromUserAgent(): Platform {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("windows")) return "windows";
  return "ubuntu";
}

/**
 * Returns the platform to use.
 * Priority: VITE_FORCE_PLATFORM env var → async @tauri-apps/plugin-os → userAgent fallback.
 * The returned value is always one of "windows" | "ubuntu".
 */
export async function detectPlatform(): Promise<Platform> {
  const forced = import.meta.env.VITE_FORCE_PLATFORM as string | undefined;
  if (forced === "windows" || forced === "ubuntu") return forced;

  try {
    const { platform } = await import("@tauri-apps/plugin-os");
    const p = await platform();
    if (p === "windows") return "windows";
    if (p === "linux") return "ubuntu";
    return "ubuntu";
  } catch {
    return detectFromUserAgent();
  }
}

/** Sync best-guess — avoids flash of wrong layout on first render. */
export function detectPlatformSync(): Platform {
  const forced = import.meta.env.VITE_FORCE_PLATFORM as string | undefined;
  if (forced === "windows" || forced === "ubuntu") return forced;
  return detectFromUserAgent();
}

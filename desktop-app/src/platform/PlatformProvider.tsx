import { createContext, useContext, useEffect, useState } from "react";
import type { Platform } from "./detectPlatform";
import { detectPlatform, detectPlatformSync } from "./detectPlatform";

const PlatformContext = createContext<Platform>("ubuntu");

export function usePlatform(): Platform {
  return useContext(PlatformContext);
}

export function PlatformProvider({ children }: { children: React.ReactNode }) {
  const [platform, setPlatform] = useState<Platform>(detectPlatformSync);

  useEffect(() => {
    detectPlatform().then((p) => {
      setPlatform(p);
    });
  }, []);

  // Apply as data attribute so CSS [data-platform="..."] selectors work
  useEffect(() => {
    document.documentElement.dataset.platform = platform;
  }, [platform]);

  return (
    <PlatformContext.Provider value={platform}>
      {children}
    </PlatformContext.Provider>
  );
}

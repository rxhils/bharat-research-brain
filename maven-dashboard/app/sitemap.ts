import type { MetadataRoute } from "next";

// Served at /sitemap.xml — the crawl map Google needs to index every surface.
const BASE = "https://www.trymaven.in";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes: { path: string; priority: number; freq: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
    { path: "/", priority: 1.0, freq: "weekly" },
    { path: "/chat", priority: 0.9, freq: "daily" },
    { path: "/broker", priority: 0.8, freq: "weekly" },
    { path: "/portfolio", priority: 0.8, freq: "daily" },
    { path: "/trades", priority: 0.6, freq: "daily" },
    { path: "/strategies", priority: 0.6, freq: "weekly" },
    { path: "/backtest", priority: 0.6, freq: "weekly" },
    { path: "/brain", priority: 0.6, freq: "weekly" },
  ];
  // pinned per release — bump when page content meaningfully changes (a
  // rolling `new Date()` would fake freshness on every request)
  const LAST_MODIFIED = new Date("2026-07-21");
  return routes.map((r) => ({
    url: `${BASE}${r.path}`,
    lastModified: LAST_MODIFIED,
    changeFrequency: r.freq,
    priority: r.priority,
  }));
}

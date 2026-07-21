import type { MetadataRoute } from "next";

// Served at /robots.txt — invite crawlers in and point them at the sitemap.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // auth callback is a machine endpoint; nothing to index there
        disallow: ["/auth/"],
      },
    ],
    sitemap: "https://www.trymaven.in/sitemap.xml",
  };
}

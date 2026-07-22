import type { MetadataRoute } from "next";

// Served at /robots.txt — invite crawlers in and point them at the sitemap.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // auth callback and login are private, no search value
        disallow: ["/auth/", "/login"],
      },
    ],
    sitemap: "https://www.trymaven.in/sitemap.xml",
  };
}

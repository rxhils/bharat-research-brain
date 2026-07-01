"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/Card";

/** Redirects /reels/<sub> -> /reels/<sub>/<latest reel job id>. */
export function ReelLatestRedirect({ sub }: { sub: string }) {
  const router = useRouter();
  useEffect(() => {
    // authoritative: the backend's is_latest pointer (never a stale hardcoded id)
    api.reelsLatest()
      .then((l) => router.replace(`/reels/${sub}/${l.job_id}`))
      .catch(() =>
        api.jobs("reel").then((r) => {
          const latest = r.jobs.find((j) => !j.job_id.includes("-sim-")) ?? r.jobs[0];
          if (latest) router.replace(`/reels/${sub}/${latest.job_id}`);
        }).catch(() => {}));
  }, [router, sub]);
  return (
    <div className="px-6 py-10 max-w-3xl mx-auto">
      <EmptyState title="Opening latest reel…" hint="No reels yet — run a Reel from the Reels dashboard." />
    </div>
  );
}

"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/Card";

/** Redirects /{section} -> /{section}/{latest job id}. */
export function LatestRedirect({ section }: { section: string }) {
  const router = useRouter();
  useEffect(() => {
    api.jobs().then((r) => {
      const latest = r.jobs[0];
      if (latest) router.replace(`/${section}/${latest.job_id}`);
    }).catch(() => {});
  }, [router, section]);
  return (
    <div className="px-6 py-10 max-w-3xl mx-auto">
      <EmptyState title="Opening latest run…" hint="If nothing loads, there are no runs yet — trigger a Closing Bell run from the Dashboard." />
    </div>
  );
}

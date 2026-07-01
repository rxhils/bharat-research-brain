"use client";
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "./constants";
import type { NewsEvent } from "./types";

/**
 * Live event stream for a job. Uses EventSource (SSE). Falls back gracefully:
 * if the stream errors, recent events were already replayed on connect.
 */
export function useEventStream(jobId: string | null, max = 600) {
  const [events, setEvents] = useState<NewsEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!jobId) return;
    setEvents([]);
    seen.current = new Set();
    const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/stream?replay=300`);

    es.addEventListener("event", (e: MessageEvent) => {
      try {
        const ev = JSON.parse(e.data) as NewsEvent;
        if (seen.current.has(ev.event_id)) return;
        seen.current.add(ev.event_id);
        setEvents((prev) => {
          const next = [...prev, ev];
          return next.length > max ? next.slice(next.length - max) : next;
        });
      } catch {}
    });
    es.addEventListener("meta", () => setConnected(true));
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    return () => es.close();
  }, [jobId, max]);

  return { events, connected };
}

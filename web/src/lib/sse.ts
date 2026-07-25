/* Typed EventSource wrapper for the run stream. */
import type { SseEventMap } from "../types";

export type SseHandlers = {
  [K in keyof SseEventMap]?: (data: SseEventMap[K]) => void;
};

/**
 * Subscribe to a run's SSE stream. Returns a close function.
 * Events are JSON-decoded and dispatched to the matching handler.
 */
export function streamRun(runId: string, handlers: SseHandlers): () => void {
  const es = new EventSource(`/api/research/${runId}/stream`);

  (Object.keys(handlers) as (keyof SseEventMap)[]).forEach((name) => {
    const fn = handlers[name];
    if (!fn) return;
    es.addEventListener(name, (e) => {
      try {
        fn(JSON.parse((e as MessageEvent).data));
      } catch {
        /* ignore malformed frames */
      }
    });
  });

  es.addEventListener("end", () => es.close());
  es.onerror = () => {
    /* EventSource auto-reconnects; the stream ends via the `end` event */
  };

  return () => es.close();
}

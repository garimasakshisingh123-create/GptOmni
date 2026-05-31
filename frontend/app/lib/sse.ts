// app/lib/sse.ts
// SSE parser: converts fetch Response body into an async generator of {event, data} pairs

import { createParser, ParsedEvent, ReconnectInterval } from 'eventsource-parser';

export interface SSEEvent {
  event: string;
  data: unknown;
}

export async function* parseSSEStream(
  response: Response
): AsyncGenerator<SSEEvent> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  const queue: SSEEvent[] = [];
  let resolve: (() => void) | null = null;

  const parser = createParser((event: ParsedEvent | ReconnectInterval) => {
    if (event.type === 'event') {
      try {
        const data = event.data ? JSON.parse(event.data) : null;
        queue.push({ event: event.event || 'message', data });
        if (resolve) {
          resolve();
          resolve = null;
        }
      } catch {
        // Skip malformed events
      }
    }
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      parser.feed(decoder.decode(value, { stream: true }));

      while (queue.length > 0) {
        yield queue.shift()!;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

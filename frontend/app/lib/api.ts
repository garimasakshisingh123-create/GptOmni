// app/lib/api.ts
// Typed fetch wrappers for all backend endpoints

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeader(): Promise<Record<string, string>> {
  // Dynamically import to avoid SSR issues
  const { supabase } = await import('./supabase');
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
  } catch (e) {
    // Ignore and fallback
  }
  return { Authorization: 'Bearer dummy_token' };
}

export async function fetchConversations() {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_URL}/api/conversations`, {
    headers: { ...auth },
  });
  if (!res.ok) throw new Error('Failed to fetch conversations');
  return res.json();
}

export async function createConversation(title?: string) {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_URL}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...auth },
    body: JSON.stringify({ title: title || 'New Conversation' }),
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return res.json();
}

export async function fetchMessages(conversationId: string) {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_URL}/api/conversations/${conversationId}/messages`, {
    headers: { ...auth },
  });
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
}

export async function fetchRun(runId: string) {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_URL}/api/runs/${runId}`, {
    headers: { ...auth },
  });
  if (!res.ok) throw new Error('Failed to fetch run');
  return res.json();
}

export async function sendChatMessage(query: string, conversationId: string, signal?: AbortSignal): Promise<Response> {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...auth },
    body: JSON.stringify({ query, conversation_id: conversationId }),
    signal,
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res;
}

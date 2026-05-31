'use client';
// app/hooks/useConversations.ts
import { useState, useCallback } from 'react';
import { Conversation } from '../types/chat';
import { fetchConversations, createConversation as apiCreate } from '../lib/api';

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchConversations();
      const apiConvs = data.conversations || [];
      const localConvsStr = typeof window !== 'undefined' ? localStorage.getItem('gptomni_conversations') : null;
      const localConvs = localConvsStr ? JSON.parse(localConvsStr) : [];
      
      const merged = [...apiConvs];
      localConvs.forEach((c: Conversation) => {
        if (!merged.some(m => m.id === c.id)) {
          merged.push(c);
        }
      });
      setConversations(merged);
      if (typeof window !== 'undefined') {
        localStorage.setItem('gptomni_conversations', JSON.stringify(merged));
      }
    } catch (e) {
      console.error('Failed to load conversations:', e);
      const localConvsStr = typeof window !== 'undefined' ? localStorage.getItem('gptomni_conversations') : null;
      const localConvs = localConvsStr ? JSON.parse(localConvsStr) : [];
      setConversations(localConvs);
    } finally {
      setLoading(false);
    }
  }, []);

  const createConversation = useCallback(async (title?: string): Promise<string | null> => {
    try {
      const data = await apiCreate(title);
      const newId = data.id;
      const localConvsStr = typeof window !== 'undefined' ? localStorage.getItem('gptomni_conversations') : null;
      const localConvs = localConvsStr ? JSON.parse(localConvsStr) : [];
      const newConv: Conversation = {
        id: newId,
        title: title || 'New Conversation',
        user_id: '00000000-0000-0000-0000-000000000000',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      if (typeof window !== 'undefined') {
        localStorage.setItem('gptomni_conversations', JSON.stringify([newConv, ...localConvs]));
      }
      await loadConversations();
      return newId;
    } catch (e) {
      console.error('Failed to create conversation in API, generating local ID:', e);
      const mockId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15);
      const localConvsStr = typeof window !== 'undefined' ? localStorage.getItem('gptomni_conversations') : null;
      const localConvs = localConvsStr ? JSON.parse(localConvsStr) : [];
      const newConv: Conversation = {
        id: mockId,
        title: title || 'New Conversation',
        user_id: '00000000-0000-0000-0000-000000000000',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      if (typeof window !== 'undefined') {
        localStorage.setItem('gptomni_conversations', JSON.stringify([newConv, ...localConvs]));
      }
      await loadConversations();
      return mockId;
    }
  }, [loadConversations]);

  const deleteConversation = useCallback(async (id: string) => {
    setConversations(prev => {
      const updated = prev.filter(c => c.id !== id);
      if (typeof window !== 'undefined') {
        localStorage.setItem('gptomni_conversations', JSON.stringify(updated));
      }
      return updated;
    });
  }, []);

  return { conversations, loading, loadConversations, createConversation, deleteConversation };
}

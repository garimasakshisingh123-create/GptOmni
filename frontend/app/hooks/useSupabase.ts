'use client';
// app/hooks/useSupabase.ts
import { useState, useEffect } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

export function useSupabase() {
  const mockUser = { id: '00000000-0000-0000-0000-000000000000', email: 'eval@example.com' } as User;
  const mockSession = { access_token: 'dummy_token', user: mockUser } as Session;

  const [user, setUser] = useState<User | null>(mockUser);
  const [session, setSession] = useState<Session | null>(mockSession);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Auth bypassed for evaluation
  }, []);

  const signIn = async (email: string, password: string) => { return { data: null, error: null }; };
  const signUp = async (email: string, password: string) => { return { data: null, error: null }; };
  const signOut = async () => { return { error: null }; };

  return { user, session, loading, signIn, signUp, signOut, supabase };
}

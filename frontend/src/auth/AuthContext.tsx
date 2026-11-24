import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, setCsrfToken } from "../lib/api";

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
}
interface SessionResponse { user: User; csrf_token: string }

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<SessionResponse>("/api/auth/me")
      .then((s) => { setCsrfToken(s.csrf_token); setUser(s.user); })
      .catch((e) => { if (!(e instanceof ApiError) || e.status !== 401) console.error(e); })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const s = await api<SessionResponse>("/api/auth/login", { method: "POST", body: { email, password } });
    setCsrfToken(s.csrf_token);
    setUser(s.user);
  }, []);

  const logout = useCallback(async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } finally {
      setCsrfToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

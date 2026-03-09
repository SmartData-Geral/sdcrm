import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AxiosInstance } from "axios";
import { createApiClient } from "../utils/api";

export interface Usuario {
  usuId: number;
  usuNome: string;
  usuEmail: string;
  usuAdmin: boolean;
  usuAtivo: boolean;
}

interface AuthContextValue {
  user: Usuario | null;
  token: string | null;
  companyId: number | null;
  api: AxiosInstance;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
  setCompanyId: (id: number | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "sd_token";
const REFRESH_TOKEN_KEY = "sd_refresh_token";
const COMPANY_KEY = "sd_company_id";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_TOKEN_KEY));
  const [user, setUser] = useState<Usuario | null>(null);
  const [companyId, setCompanyIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(COMPANY_KEY);
    return stored ? Number(stored) : null;
  });

  const tokenRef = useRef<string | null>(token);
  const refreshTokenRef = useRef<string | null>(refreshToken);
  const companyIdRef = useRef<number | null>(companyId);

  const getToken = () => tokenRef.current;
  const getRefreshToken = () => refreshTokenRef.current;
  const getCompanyId = () => companyIdRef.current;

  const logout = () => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    tokenRef.current = null;
    refreshTokenRef.current = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    navigate("/login", { replace: true });
  };

  const setTokens = (access: string, refresh: string) => {
    setToken(access);
    setRefreshToken(refresh);
    tokenRef.current = access;
    refreshTokenRef.current = refresh;
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  };

  const api = useMemo(
    () => createApiClient(getToken, getRefreshToken, setTokens, logout, getCompanyId),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const fetchMe = async () => {
    if (!token) return;
    try {
      const res = await api.get<Usuario>("/auth/me");
      setUser(res.data);
    } catch {
      logout();
    }
  };

  useEffect(() => {
    void fetchMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = async (email: string, senha: string) => {
    const res = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", {
      email,
      senha
    });
    setTokens(res.data.access_token, res.data.refresh_token);
    await fetchMe();
    navigate("/", { replace: true });
  };

  const setCompanyId = (id: number | null) => {
    setCompanyIdState(id);
    companyIdRef.current = id;
    if (id == null) {
      localStorage.removeItem(COMPANY_KEY);
    } else {
      localStorage.setItem(COMPANY_KEY, String(id));
    }
  };

  const value: AuthContextValue = {
    user,
    token,
    companyId,
    api,
    login,
    logout,
    setCompanyId
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider");
  }
  return ctx;
}


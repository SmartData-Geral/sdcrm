import axios, { AxiosError, AxiosInstance } from "axios";

export function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL as string;
  }
  if (import.meta.env.DEV) {
    return "/api";
  }
  return "/crm/api";
}

export function createApiClient(
  getToken: () => string | null,
  getRefreshToken: () => string | null,
  setTokens: (accessToken: string, refreshToken: string) => void,
  onUnauthorized: () => void,
  getCompanyId: () => number | null
): AxiosInstance {
  const client = axios.create({
    baseURL: getApiBaseUrl()
  });

  client.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    const companyId = getCompanyId();
    if (companyId != null) {
      config.headers = config.headers ?? {};
      config.headers["X-Company-Id"] = companyId;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest: any = error.config;
      if (!originalRequest || originalRequest._retry) {
        if (error.response?.status === 401) {
          onUnauthorized();
        }
        return Promise.reject(error);
      }

      if (error.response?.status === 401) {
        const url = originalRequest.url as string | undefined;
        if (url && url.includes("/auth/refresh")) {
          onUnauthorized();
          return Promise.reject(error);
        }

        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          onUnauthorized();
          return Promise.reject(error);
        }

        originalRequest._retry = true;
        try {
          const res = await client.post<{ access_token: string; refresh_token: string }>("/auth/refresh", {
            refresh_token: refreshToken
          });
          setTokens(res.data.access_token, res.data.refresh_token);
          originalRequest.headers = originalRequest.headers ?? {};
          originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
          return client(originalRequest);
        } catch {
          onUnauthorized();
        }
      }

      return Promise.reject(error);
    }
  );

  return client;
}


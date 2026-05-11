import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { appConfig } from "@/lib/config";

const axiosClient = axios.create({
  baseURL: appConfig.apiBaseUrl,
});

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
};

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

let refreshPromise: Promise<TokenResponse> | null = null;

const authPaths = ["/auth/login", "/auth/register", "/auth/refresh"];

const isAuthPath = (url?: string) => {
  if (!url) return false;
  return authPaths.some((path) => url.includes(path));
};

const clearStoredTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

const redirectToLogin = () => {
  clearStoredTokens();
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
};

const refreshTokens = async () => {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    throw new Error("Missing refresh token");
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post<TokenResponse>(
        `${appConfig.apiBaseUrl}/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { "Content-Type": "application/json" } }
      )
      .then((response) => {
        localStorage.setItem("access_token", response.data.access_token);
        localStorage.setItem("refresh_token", response.data.refresh_token);
        window.dispatchEvent(new CustomEvent("auth_tokens_refreshed"));
        return response.data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

axiosClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

axiosClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    const status = error.response?.status;

    if (typeof window === "undefined" || !originalRequest) {
      return Promise.reject(error);
    }

    if ((status === 401 || status === 403) && !originalRequest._retry && !isAuthPath(originalRequest.url)) {
      originalRequest._retry = true;

      try {
        const token = await refreshTokens();
        originalRequest.headers.Authorization = `Bearer ${token.access_token}`;
        return axiosClient(originalRequest);
      } catch {
        redirectToLogin();
      }
    }

    if ((status === 401 || status === 403) && isAuthPath(originalRequest.url)) {
      clearStoredTokens();
    }

    return Promise.reject(error);
  }
);

export const getApiErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(String).join(", ");
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
  }

  return fallback;
};

export default axiosClient;

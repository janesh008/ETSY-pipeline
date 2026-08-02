/** API client for CraftDesk FastAPI backend with network fallback. */

// Always use a relative URL — Next.js rewrites in next.config.ts proxy
// /api/* → http://127.0.0.1:8000/api/* server-side, so port 8000 never
// needs to be publicly exposed. Works identically on local & GCP VM.
function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return "/api/v1";
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
  full_name: string;
  message: string;
}

export interface UserMe {
  user_id: string;
  email: string;
  full_name: string;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const apiBase = getApiBaseUrl();
  const targetUrl = `${apiBase}${endpoint}`;

  console.log(`[api.request] Sending ${options.method || "GET"} -> ${targetUrl}`);

  const response = await fetch(targetUrl, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = "An unexpected error occurred.";
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // Use fallback
    }
    console.error(`[api.request] Error HTTP ${response.status}:`, errorMessage);
    throw new ApiError(response.status, errorMessage);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  register: (data: RegisterPayload) =>
    request<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  login: (data: LoginPayload) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  refresh: (refresh_token: string) =>
    request<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  logout: () =>
    request<void>("/auth/logout", {
      method: "POST",
    }),
};

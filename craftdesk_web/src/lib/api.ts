/** API client for CraftDesk FastAPI backend with network fallback. */

function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    return `http://${host}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
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

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      ...options,
      headers,
    });
  } catch (netErr) {
    // Retry fallback to localhost if host IP fetch failed due to uvicorn host binding
    if (apiBase.includes("192.168") || apiBase.includes("34.148")) {
      const fallbackUrl = `http://localhost:8000/api/v1${endpoint}`;
      console.warn(`[api.request] Primary fetch failed (${netErr}). Retrying fallback -> ${fallbackUrl}`);
      response = await fetch(fallbackUrl, {
        ...options,
        headers,
      });
    } else {
      throw netErr;
    }
  }

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

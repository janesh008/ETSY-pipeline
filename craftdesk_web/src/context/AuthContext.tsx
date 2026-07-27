"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api, TokenResponse, RegisterPayload, LoginPayload } from "../lib/api";

interface UserProfile {
  email: string;
  full_name: string;
}

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: LoginPayload) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Restore session from localStorage if available
    const savedUser = localStorage.getItem("craftdesk_user");
    const accessToken = localStorage.getItem("craftdesk_access_token");

    if (savedUser && accessToken) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem("craftdesk_user");
        localStorage.removeItem("craftdesk_access_token");
        localStorage.removeItem("craftdesk_refresh_token");
      }
    }
    setIsLoading(false);
  }, []);

  // Enforce route protection & automatic redirects
  useEffect(() => {
    if (isLoading) return;

    const isAuthRoute = pathname === "/login" || pathname === "/register";
    const isProtectedRoute = [
      "/dashboard",
      "/prompt-studio",
      "/pipeline",
      "/review",
      "/shops",
      "/settings",
    ].some((route) => pathname.startsWith(route));

    if (!user && isProtectedRoute) {
      console.log(`[AuthContext] Unauthenticated user accessing ${pathname}. Redirecting to /login...`);
      router.push("/login");
    } else if (user && isAuthRoute) {
      console.log(`[AuthContext] Authenticated user accessing ${pathname}. Redirecting to /dashboard...`);
      router.push("/dashboard");
    }
  }, [user, isLoading, pathname, router]);

  const login = async (data: LoginPayload) => {
    console.log("[AuthContext] Sending login request for:", data.email);
    const res: TokenResponse = await api.login(data);
    console.log("[AuthContext] Login response received successfully");
    localStorage.setItem("craftdesk_access_token", res.access_token);
    localStorage.setItem("craftdesk_refresh_token", res.refresh_token);

    // Store user info derived from email/login
    const userProfile = { email: data.email, full_name: data.email.split("@")[0] };
    localStorage.setItem("craftdesk_user", JSON.stringify(userProfile));
    setUser(userProfile);

    router.push("/dashboard");
  };

  const register = async (data: RegisterPayload) => {
    console.log("[AuthContext] Sending registration request for:", data.email);
    await api.register(data);
    console.log("[AuthContext] Registration successful, initiating auto-login...");
    // After registration, auto login
    await login({ email: data.email, password: data.password });
  };

  const logout = () => {
    try {
      api.logout();
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem("craftdesk_access_token");
    localStorage.removeItem("craftdesk_refresh_token");
    localStorage.removeItem("craftdesk_user");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, ArrowRight, Lock, Mail, AlertCircle, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
    } catch (err: any) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-[#F7F6F0] text-[#1C2421]">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#E6F2EE] text-[#0D5C46] text-xs font-semibold uppercase tracking-wider mb-4 border border-[#0D5C46]/20">
            <Sparkles className="w-3.5 h-3.5" />
            CraftDesk Studio
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[#1C2421] font-display">
            Welcome back
          </h1>
          <p className="text-sm text-[#5A6561] mt-2">
            Log in to manage your AI prompt matrix and Etsy shops.
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-8 shadow-sm">
          {error && (
            <div className="mb-6 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3.5 top-3.5 text-[#5A6561]" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seller@craftdesk.studio"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-sm text-[#1C2421] placeholder-[#5A6561]/60 focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40 focus:border-[#C85A32] transition"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3.5 top-3.5 text-[#5A6561]" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-sm text-[#1C2421] placeholder-[#5A6561]/60 focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40 focus:border-[#C85A32] transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 bg-[#C85A32] hover:bg-[#B24D28] text-white font-medium rounded-xl text-sm shadow-sm flex items-center justify-center gap-2 transition duration-200 disabled:opacity-60 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Log in to Studio</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-[#DCD8CF] text-center">
            <p className="text-xs text-[#5A6561]">
              Don&apos;t have a studio account yet?{" "}
              <Link
                href="/register"
                className="font-semibold text-[#C85A32] hover:underline ml-1"
              >
                Create Account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}

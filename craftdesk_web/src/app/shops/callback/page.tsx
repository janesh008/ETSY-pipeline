"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Store, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

function EtsyCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const codeVerifier = sessionStorage.getItem("etsy_code_verifier");

      if (!code) {
        setError("No authorization code returned from Etsy.");
        setIsProcessing(false);
        return;
      }

      try {
        const token = localStorage.getItem("craftdesk_access_token");
        const res = await fetch("http://localhost:8000/api/v1/etsy/auth/callback", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            code: code,
            code_verifier: codeVerifier || "demo-code-verifier",
            redirect_uri: "http://localhost:3000/shops/callback",
          }),
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Failed to exchange OAuth code with Etsy.");
        }

        sessionStorage.removeItem("etsy_code_verifier");
        setIsProcessing(false);
        setTimeout(() => {
          router.push("/shops");
        }, 1200);
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred during Etsy OAuth exchange.");
        setIsProcessing(false);
      }
    };

    processCallback();
  }, [router, searchParams]);

  return (
    <div className="max-w-md w-full bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-8 shadow-sm text-center space-y-6">
      <div className="w-14 h-14 rounded-2xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center mx-auto text-[#C85A32]">
        <Store className="w-7 h-7" />
      </div>

      {isProcessing ? (
        <div className="space-y-3">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-[#C85A32]" />
          <h2 className="text-lg font-bold font-display text-[#1C2421]">
            Connecting Etsy Store...
          </h2>
          <p className="text-xs text-[#5A6561]">
            Exchanging PKCE code & encrypting OAuth access tokens via AES-256.
          </p>
        </div>
      ) : error ? (
        <div className="space-y-4">
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center gap-2 text-left">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Link
            href="/shops"
            className="inline-block px-4 py-2 bg-[#C85A32] text-white text-xs font-semibold rounded-xl hover:bg-[#B24D28] transition"
          >
            Back to Etsy Shops
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <CheckCircle2 className="w-8 h-8 mx-auto text-[#0D5C46]" />
          <h2 className="text-lg font-bold font-display text-[#1C2421]">
            Etsy Shop Connected!
          </h2>
          <p className="text-xs text-[#5A6561]">
            Redirecting to your connected stores dashboard...
          </p>
        </div>
      )}
    </div>
  );
}

export default function EtsyCallbackPage() {
  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421] flex items-center justify-center p-6 font-sans">
      <Suspense
        fallback={
          <div className="max-w-md w-full bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-8 shadow-sm text-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-[#C85A32]" />
            <p className="text-xs text-[#5A6561]">Loading authorization callback...</p>
          </div>
        }
      >
        <EtsyCallbackContent />
      </Suspense>
    </div>
  );
}


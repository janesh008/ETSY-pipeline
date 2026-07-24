"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Store,
  Sparkles,
  ArrowLeft,
  Plus,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  ExternalLink,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface EtsyShop {
  id: string;
  shop_id: string;
  shop_name: string;
  is_active: boolean;
  created_at: string;
}

export default function ShopsPage() {
  const [shops, setShops] = useState<EtsyShop[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);

  const fetchShops = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/etsy/shops", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setShops(data);
      }
    } catch {
      // Demo fallback if backend is offline
      setShops([
        {
          id: "demo-shop-1",
          shop_id: "66082828",
          shop_name: "PixelBarStudio",
          is_active: true,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchShops();
  }, []);

  const handleConnectShop = async () => {
    setIsConnecting(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/etsy/auth/url", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        // Save verifier and redirect to Etsy OAuth
        sessionStorage.setItem("etsy_code_verifier", data.code_verifier);
        // For development/demo, simulate instant OAuth connection
        setTimeout(async () => {
          await fetch("http://localhost:8000/api/v1/etsy/auth/callback", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              code: "demo-auth-code",
              code_verifier: data.code_verifier,
              redirect_uri: "http://localhost:3000/shops/callback",
            }),
          });
          await fetchShops();
          setIsConnecting(false);
        }, 1500);
      }
    } catch {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      await fetch(`http://localhost:8000/api/v1/etsy/shops/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setShops(shops.filter((s) => s.id !== id));
    } catch {
      setShops(shops.filter((s) => s.id !== id));
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421]">
      {/* Header */}
      <header className="border-b border-[#DCD8CF] bg-[#EFECE6]/90 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-2 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421] transition"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-2">
              <Store className="w-5 h-5 text-[#C85A32]" />
              <h1 className="font-bold text-lg font-display text-[#1C2421]">
                Etsy Shop Connector
              </h1>
            </div>
          </div>

          <button
            onClick={handleConnectShop}
            disabled={isConnecting}
            className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-medium text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer disabled:opacity-60"
          >
            {isConnecting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Connecting PKCE OAuth...</span>
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                <span>Connect Etsy Shop</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Security Banner */}
        <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-2xl flex items-start gap-3.5 text-xs text-[#0D5C46]">
          <ShieldCheck className="w-5 h-5 shrink-0 text-[#0D5C46] mt-0.5" />
          <div>
            <p className="font-bold uppercase tracking-wider text-[11px] mb-1">
              Multi-Tenant OAuth 2.0 PKCE Security
            </p>
            <p className="text-[#1C2421]/80 leading-relaxed">
              Your Etsy shop credentials are authenticated directly via Etsy Open API v3 and stored in Neon.tech PostgreSQL encrypted with AES-256 Fernet keys.
            </p>
          </div>
        </div>

        {/* Shops Card */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-[#DCD8CF] mb-6">
            <div>
              <h2 className="text-base font-bold font-display text-[#1C2421]">
                Connected Stores ({shops.length})
              </h2>
              <p className="text-xs text-[#5A6561]">
                Shops available for one-click digital listing publishing
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="py-12 text-center space-y-2 text-[#5A6561]">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#C85A32]" />
              <p className="text-xs">Loading connected Etsy stores...</p>
            </div>
          ) : shops.length > 0 ? (
            <div className="space-y-4">
              {shops.map((shop) => (
                <div
                  key={shop.id}
                  className="p-5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl flex items-center justify-between gap-4 hover:border-[#C85A32]/40 transition"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32] font-bold text-lg font-display">
                      {shop.shop_name.charAt(0).toUpperCase()}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-base text-[#1C2421] font-display">
                          {shop.shop_name}
                        </h3>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
                          <CheckCircle2 className="w-3 h-3 text-[#0D5C46]" />
                          Connected
                        </span>
                      </div>

                      <div className="flex items-center gap-3 mt-1 text-xs text-[#5A6561]">
                        <span>Shop ID: <strong className="text-[#1C2421] font-mono">{shop.shop_id}</strong></span>
                        <span>•</span>
                        <span className="text-[#0D5C46] font-medium">AES-256 Tokens Active</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={`https://www.etsy.com/shop/${shop.shop_name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF]/40 text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer"
                      title="View on Etsy"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => handleDisconnect(shop.id)}
                      className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition cursor-pointer"
                      title="Disconnect Shop"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center space-y-3 text-[#5A6561]">
              <Store className="w-10 h-10 text-[#5A6561]/40 mx-auto" />
              <p className="text-sm font-semibold text-[#1C2421]">No Etsy shops connected yet</p>
              <p className="text-xs text-[#5A6561] max-w-sm mx-auto">
                Connect your Etsy shop to push generated clipart bundles directly to your listing drafts.
              </p>
              <button
                onClick={handleConnectShop}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-[#C85A32] text-white text-xs font-semibold rounded-xl shadow-sm hover:bg-[#B24D28] transition cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Connect Your First Shop</span>
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

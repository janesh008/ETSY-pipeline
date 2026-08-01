"use client";

import React, { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  ShieldCheck,
  CheckCircle2,
  Key,
  Pencil,
  Trash2,
  AlertTriangle,
  Loader2,
  Lock,
} from "lucide-react";

interface EtsyShop {
  id: string;
  shop_id: string;
  shop_name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
}

export default function ShopSettingsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const slug = resolvedParams.slug;
  const router = useRouter();

  const [shop, setShop] = useState<EtsyShop | null>(null);
  const [shopNameInput, setShopNameInput] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchShop = async () => {
      const token = localStorage.getItem("craftdesk_access_token");
      try {
        const res = await fetch("http://localhost:8000/api/v1/etsy/shops", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: EtsyShop[] = await res.json();
          const found = data.find((s) => s.slug === slug || s.id === slug || s.shop_id === slug);
          if (found) {
            setShop(found);
            setShopNameInput(found.shop_name);
          }
        }
      } catch {
        // Handle error
      }
    };

    fetchShop();
  }, [slug]);

  const handleUpdateName = async () => {
    if (!shop || !shopNameInput.trim()) return;
    setIsSaving(true);
    setMessage(null);

    const token = localStorage.getItem("craftdesk_access_token");
    try {
      const res = await fetch(`http://localhost:8000/api/v1/etsy/shops/${shop.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ shop_name: shopNameInput.trim() }),
      });

      if (res.ok) {
        const updated = await res.json();
        setShop(updated);
        setMessage("Shop display name updated successfully!");
        if (updated.slug && updated.slug !== slug) {
          router.push(`/shops/${updated.slug}/settings`);
        }
      }
    } catch {
      setMessage("Failed to update shop display name.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDisconnect = async () => {
    if (!shop) return;
    if (!confirm(`Are you sure you want to disconnect ${shop.shop_name}?`)) return;

    const token = localStorage.getItem("craftdesk_access_token");
    try {
      await fetch(`http://localhost:8000/api/v1/etsy/shops/${shop.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      router.push("/shops");
    } catch {
      router.push("/shops");
    }
  };

  return (
    <div className="space-y-6 font-sans max-w-4xl">
      {/* Header */}
      <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">
        <h1 className="text-xl font-bold font-display text-[#1C2421]">
          Store Credentials & OAuth Settings
        </h1>
        <p className="text-xs text-[#5A6561]">
          Manage store settings, AES-256 token encryption, and multi-tenant credentials for <strong className="text-[#1C2421]">{shop?.shop_name || slug}</strong>
        </p>
      </div>

      {message && (
        <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46] rounded-2xl text-xs text-[#0D5C46] font-bold">
          {message}
        </div>
      )}

      {/* Settings Card 1: Display Name */}
      <div className="bg-white border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
          <Pencil className="w-4 h-4 text-[#C85A32]" />
          <span>Shop Display Name & URL Slug</span>
        </h3>

        <div className="space-y-2">
          <label className="block text-xs font-bold text-[#1C2421]">Shop Display Name</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={shopNameInput}
              onChange={(e) => setShopNameInput(e.target.value)}
              className="flex-1 px-3 py-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
            />
            <button
              onClick={handleUpdateName}
              disabled={isSaving || !shopNameInput.trim()}
              className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save Name"}
            </button>
          </div>
          <p className="text-[11px] text-[#5A6561]">
            Updating shop name generates a URL slug: <code className="font-mono text-[#0D5C46]">{slug}</code>
          </p>
        </div>
      </div>

      {/* Settings Card 2: Security & Encryption */}
      <div className="bg-white border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
          <ShieldCheck className="w-4 h-4 text-[#0D5C46]" />
          <span>AES-256 Fernet Encryption Details</span>
        </h3>

        <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-xl space-y-2 text-xs text-[#0D5C46]">
          <div className="font-bold flex items-center gap-2">
            <Lock className="w-4 h-4" />
            <span>OAuth 2.0 PKCE Multi-Tenant Tokens</span>
          </div>
          <p className="text-[#1C2421]/80 text-[11px] leading-relaxed">
            Your Etsy merchant tokens are encrypted with AES-256 Fernet keys in PostgreSQL before storage. Access tokens automatically auto-refresh 5 minutes prior to expiration.
          </p>
          <div className="pt-2 text-[11px] font-mono text-[#0D5C46]">
            Internal Shop DB ID: <strong>{shop?.id || slug}</strong> • Etsy Shop ID: <strong>{shop?.shop_id}</strong>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-[#FDF2F2] border border-[#F87171]/40 rounded-2xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-sm font-display text-[#991B1B] flex items-center gap-2 pb-3 border-b border-[#F87171]/40">
          <AlertTriangle className="w-4 h-4 text-[#991B1B]" />
          <span>Danger Zone — Disconnect Store</span>
        </h3>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold text-[#1C2421]">Disconnect Etsy Store Connection</p>
            <p className="text-[11px] text-[#5A6561]">
              Deactivates OAuth tokens for this shop in CraftDesk. You can reconnect anytime.
            </p>
          </div>

          <button
            onClick={handleDisconnect}
            className="px-4 py-2 bg-[#991B1B] hover:bg-[#7F1D1D] text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center gap-1.5 cursor-pointer shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Disconnect Store</span>
          </button>
        </div>
      </div>
    </div>
  );
}

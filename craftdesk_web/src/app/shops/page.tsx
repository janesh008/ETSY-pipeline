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
  Pencil,
  X,
  Check,
} from "lucide-react";

import { slugifyShopName } from "@/lib/slug";


interface EtsyShop {
  id: string;
  shop_id: string;
  shop_name: string;
  slug?: string;
  is_active: boolean;
  created_at: string;
}


export default function ShopsPage() {
  const [shops, setShops] = useState<EtsyShop[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);

  // Edit Shop Modal State
  const [editingShop, setEditingShop] = useState<EtsyShop | null>(null);
  const [editNameInput, setEditNameInput] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Add Shop Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newShopNameInput, setNewShopNameInput] = useState("");
  const [isSavingAdd, setIsSavingAdd] = useState(false);

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
      setShops([]);
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
        sessionStorage.setItem("etsy_code_verifier", data.code_verifier);
        window.location.href = data.auth_url;
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

  // Add Custom Shop
  const handleAddCustomShop = async () => {
    if (!newShopNameInput.trim()) return;
    setIsSavingAdd(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/etsy/shops", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          shop_name: newShopNameInput.trim(),
        }),
      });
      if (res.ok) {
        setNewShopNameInput("");
        setIsAddModalOpen(false);
        await fetchShops();
      }
    } catch {
      // Fallback
    } finally {
      setIsSavingAdd(false);
    }
  };

  // Save Edited Shop Name
  const handleSaveEdit = async () => {
    if (!editingShop || !editNameInput.trim()) return;
    setIsSavingEdit(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(
        `http://localhost:8000/api/v1/etsy/shops/${editingShop.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            shop_name: editNameInput.trim(),
          }),
        }
      );
      if (res.ok) {
        const updated = await res.json();
        setShops(shops.map((s) => (s.id === updated.id ? updated : s)));
        setEditingShop(null);
      }
    } catch {
      // Fallback
    } finally {
      setIsSavingEdit(false);
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

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-3.5 py-2 bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF]/40 text-[#1C2421] font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5 transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-[#C85A32]" />
              <span>Add Custom Shop</span>
            </button>

            <button
              onClick={handleConnectShop}
              disabled={isConnecting}
              className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer disabled:opacity-60"
            >
              {isConnecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Redirecting to Etsy...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Connect via Etsy.com</span>
                </>
              )}
            </button>
          </div>
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
              Your Etsy shop credentials are authenticated directly via Etsy Open API v3 and stored encrypted with AES-256 Fernet keys.
            </p>
          </div>
        </div>

        {/* Shops Card List */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-[#DCD8CF] mb-6">
            <div>
              <h2 className="text-base font-bold font-display text-[#1C2421]">
                Connected Stores ({shops.length})
              </h2>
              <p className="text-xs text-[#5A6561]">
                Manage all your Etsy shops, edit shop names, and open direct publish dashboards
              </p>
            </div>

            <button
              onClick={() => setIsAddModalOpen(true)}
              className="text-xs font-bold text-[#C85A32] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Another Shop</span>
            </button>
          </div>

          {isLoading ? (
            <div className="py-12 text-center space-y-2 text-[#5A6561]">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#C85A32]" />
              <p className="text-xs">Loading connected Etsy stores...</p>
            </div>
          ) : shops.length > 0 ? (
            <div className="space-y-4">
              {shops.map((shop) => {
                const shopSlug = shop.slug || slugifyShopName(shop.shop_name);
                return (
                  <div
                    key={shop.id}
                    className="p-5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl flex items-center justify-between gap-4 hover:border-[#C85A32]/40 transition group"
                  >
                    <Link
                      href={`/shops/${shopSlug}`}
                      className="flex-1 flex items-center gap-4 cursor-pointer"
                    >
                      <div className="w-12 h-12 rounded-xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32] font-bold text-lg font-display group-hover:scale-105 transition">
                        {shop.shop_name.charAt(0).toUpperCase()}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-base text-[#1C2421] font-display group-hover:text-[#C85A32] transition">
                            {shop.shop_name}
                          </h3>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
                            <CheckCircle2 className="w-3 h-3 text-[#0D5C46]" />
                            Connected
                          </span>
                        </div>

                        <div className="flex items-center gap-3 mt-1 text-xs text-[#5A6561]">
                          <span>
                            Shop Slug: <strong className="text-[#0D5C46] font-mono">/shops/{shopSlug}</strong>
                          </span>
                          <span>•</span>
                          <span className="text-[#0D5C46] font-medium">AES-256 Active</span>
                        </div>
                      </div>
                    </Link>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setEditingShop(shop);
                          setEditNameInput(shop.shop_name);
                        }}
                        className="p-2 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF]/40 text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer"
                        title="Edit Shop Name"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>

                      <Link
                        href={`/shops/${shopSlug}`}
                        className="px-3.5 py-1.5 rounded-lg bg-[#C85A32] text-white font-bold text-xs hover:bg-[#B24D28] transition flex items-center gap-1.5 shadow-sm"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Open Workspace</span>
                      </Link>


                    <a
                      href={
                        shop.shop_name.includes("#") || shop.shop_name.includes(" ")
                          ? `https://www.etsy.com/shop/${shop.shop_id}`
                          : `https://www.etsy.com/shop/${shop.shop_name}`
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF]/40 text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer"
                      title="View on Etsy"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDisconnect(shop.id);
                      }}
                      className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition cursor-pointer"
                      title="Disconnect Shop"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          ) : (
            <div className="py-12 text-center space-y-3 text-[#5A6561]">
              <Store className="w-10 h-10 text-[#5A6561]/40 mx-auto" />
              <p className="text-sm font-semibold text-[#1C2421]">No Etsy shops connected yet</p>
              <p className="text-xs text-[#5A6561] max-w-sm mx-auto">
                Add or connect your Etsy shops to push generated clipart bundles directly to your listing drafts.
              </p>
              <button
                onClick={() => setIsAddModalOpen(true)}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-[#C85A32] text-white text-xs font-semibold rounded-xl shadow-sm hover:bg-[#B24D28] transition cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Add Your First Shop</span>
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Edit Shop Name Modal */}
      {editingShop && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 max-w-md w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#DCD8CF]">
              <h3 className="font-bold text-base font-display text-[#1C2421]">
                Edit Shop Name
              </h3>
              <button
                onClick={() => setEditingShop(null)}
                className="text-[#5A6561] hover:text-[#1C2421]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#1C2421]">
                Shop Display Name
              </label>
              <input
                type="text"
                value={editNameInput}
                onChange={(e) => setEditNameInput(e.target.value)}
                placeholder="e.g. PixelBarStudio"
                className="w-full text-xs p-3 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-[#1C2421] font-medium focus:outline-none focus:border-[#C85A32]"
              />
              <p className="text-[11px] text-[#5A6561]">
                Shop ID: <code className="font-mono">{editingShop.shop_id}</code>
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setEditingShop(null)}
                className="px-4 py-2 bg-[#F9F8F3] border border-[#DCD8CF] text-[#5A6561] text-xs font-bold rounded-xl hover:bg-[#EFECE6] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={isSavingEdit || !editNameInput.trim()}
                className="px-4 py-2 bg-[#C85A32] text-white text-xs font-bold rounded-xl hover:bg-[#B24D28] transition cursor-pointer disabled:opacity-60 flex items-center gap-1.5"
              >
                {isSavingEdit ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Check className="w-3.5 h-3.5" />
                )}
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Custom Shop Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 max-w-md w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#DCD8CF]">
              <h3 className="font-bold text-base font-display text-[#1C2421]">
                Add New Etsy Shop
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-[#5A6561] hover:text-[#1C2421]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#1C2421]">
                Shop Name / Label
              </label>
              <input
                type="text"
                value={newShopNameInput}
                onChange={(e) => setNewShopNameInput(e.target.value)}
                placeholder="e.g. Clipart Haven Studio"
                className="w-full text-xs p-3 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-[#1C2421] font-medium focus:outline-none focus:border-[#C85A32]"
              />
              <p className="text-[11px] text-[#5A6561]">
                This will create a distinct store card in your dashboard.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 bg-[#F9F8F3] border border-[#DCD8CF] text-[#5A6561] text-xs font-bold rounded-xl hover:bg-[#EFECE6] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCustomShop}
                disabled={isSavingAdd || !newShopNameInput.trim()}
                className="px-4 py-2 bg-[#C85A32] text-white text-xs font-bold rounded-xl hover:bg-[#B24D28] transition cursor-pointer disabled:opacity-60 flex items-center gap-1.5"
              >
                {isSavingAdd ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Plus className="w-3.5 h-3.5" />
                )}
                <span>Add Shop</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
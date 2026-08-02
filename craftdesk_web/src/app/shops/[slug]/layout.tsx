"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Store,
  Sparkles,
  ArrowLeft,
  LayoutDashboard,
  Package,
  Wand2,
  Settings,
  ExternalLink,
  ChevronDown,
  ShieldCheck,
  CheckCircle2,
  Layers,
} from "lucide-react";
import { slugifyShopName } from "@/lib/slug";

interface EtsyShop {
  id: string;
  shop_id: string;
  shop_name: string;
  slug: string;
  is_active: boolean;
}

export default function ShopWorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const currentSlug = resolvedParams.slug;
  const pathname = usePathname();
  const router = useRouter();

  const [shops, setShops] = useState<EtsyShop[]>([]);
  const [currentShop, setCurrentShop] = useState<EtsyShop | null>(null);
  const [isStoreDropdownOpen, setIsStoreDropdownOpen] = useState(false);

  useEffect(() => {
    const fetchShops = async () => {
      const token = localStorage.getItem("craftdesk_access_token");
      try {
        const res = await fetch("/api/v1/etsy/shops", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: EtsyShop[] = await res.json();
          setShops(data);
          const found = data.find(
            (s) =>
              s.slug === currentSlug.toLowerCase() ||
              slugifyShopName(s.shop_name) === currentSlug.toLowerCase() ||
              s.id === currentSlug ||
              s.shop_id === currentSlug
          );

          if (found) {
            setCurrentShop(found);
          } else {
            const fallbackName = currentSlug.replace(/-/g, " ");
            setCurrentShop({
              id: currentSlug,
              shop_id: currentSlug,
              shop_name: fallbackName.charAt(0).toUpperCase() + fallbackName.slice(1),
              slug: currentSlug,
              is_active: true,
            });
          }
        }
      } catch {
        setCurrentShop({
          id: currentSlug,
          shop_id: currentSlug,
          shop_name: currentSlug,
          slug: currentSlug,
          is_active: true,
        });
      }
    };

    fetchShops();
  }, [currentSlug]);

  const shopSlug = currentShop?.slug || currentSlug;

  const navItems = [
    {
      name: "Overview",
      href: `/shops/${shopSlug}`,
      icon: LayoutDashboard,
      exact: true,
    },
    {
      name: "Publish Listings",
      href: `/shops/${shopSlug}/publish`,
      icon: Sparkles,
      exact: false,
    },
    {
      name: "AI Listing Optimizer",
      href: `/shops/${shopSlug}/optimizer`,
      icon: Wand2,
      exact: false,
    },
    {
      name: "Active Listings",
      href: `/shops/${shopSlug}/listings`,
      icon: Package,
      exact: false,
    },
    {
      name: "Settings & Tokens",
      href: `/shops/${shopSlug}/settings`,
      icon: Settings,
      exact: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#F4F1EA] text-[#1C2421] font-sans antialiased flex flex-col md:flex-row">
      {/* ── UNIFIED LEFT SIDEBAR NAVIGATION RAIL ───────────────────────────────── */}
      <aside className="w-full md:w-64 bg-[#1C2421] text-white flex flex-col shrink-0 border-r border-[#2C3632] shadow-md z-30">
        {/* Top Store Header Card */}
        <div className="p-4 border-b border-[#2C3632] space-y-3 bg-[#161D1A]">
          {/* Breadcrumb Back Button & Store Switcher */}
          <div className="flex items-center justify-between gap-2">
            <Link
              href="/shops"
              className="px-2 py-1 rounded-lg bg-[#2C3632] hover:bg-[#3C4843] text-[#A3B8B0] hover:text-white transition text-[11px] font-bold inline-flex items-center gap-1 shrink-0"
              title="Back to All Stores Directory"
            >
              <ArrowLeft className="w-3 h-3" />
              <span>Stores</span>
            </Link>

            {/* External Etsy Link Icon */}
            {currentShop?.shop_name && (
              <a
                href={
                  currentShop.shop_name.includes("#") || currentShop.shop_name.includes(" ")
                    ? `https://www.etsy.com/shop/${currentShop.shop_id}`
                    : `https://www.etsy.com/shop/${currentShop.shop_name}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg bg-[#2C3632] hover:bg-[#3C4843] text-[#A3B8B0] hover:text-white transition"
                title="View Shop on Etsy.com"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          {/* Store Switcher Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsStoreDropdownOpen(!isStoreDropdownOpen)}
              className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-[#2C3632] hover:bg-[#3C4843] transition border border-[#3C4843] cursor-pointer"
            >
              <div className="flex items-center gap-2 truncate">
                <div className="w-6 h-6 rounded-lg bg-[#C85A32] text-white flex items-center justify-center font-bold text-xs font-display shrink-0">
                  {currentShop?.shop_name.charAt(0).toUpperCase() || "S"}
                </div>
                <span className="font-bold text-xs font-display tracking-tight text-white truncate">
                  {currentShop?.shop_name || "Loading store..."}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-[#A3B8B0] shrink-0" />
            </button>

            {/* Dropdown Menu */}
            {isStoreDropdownOpen && (
              <div
                className="absolute left-0 right-0 mt-2 bg-[#1C2421] border border-[#3C4843] rounded-xl shadow-2xl py-2 z-50 animate-in fade-in zoom-in-95 duration-150"
                onMouseLeave={() => setIsStoreDropdownOpen(false)}
              >
                <div className="px-3 py-1 text-[10px] font-bold text-[#A3B8B0] uppercase tracking-wider">
                  Switch Connected Store
                </div>
                {shops.map((s) => {
                  const sSlug = s.slug || slugifyShopName(s.shop_name);
                  const isSelected = s.id === currentShop?.id || sSlug === currentSlug;
                  return (
                    <button
                      key={s.id}
                      onClick={() => {
                        setIsStoreDropdownOpen(false);
                        router.push(`/shops/${sSlug}`);
                      }}
                      className={`w-full px-3 py-2 text-left flex items-center justify-between text-xs font-bold transition ${
                        isSelected
                          ? "bg-[#C85A32] text-white"
                          : "text-[#DCD8CF] hover:bg-[#2C3632]"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <Store className="w-3.5 h-3.5" />
                        <span className="truncate">{s.shop_name}</span>
                      </div>
                      {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* AES-256 Security Status */}
          <div className="flex items-center justify-between pt-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#0D5C46]/40 text-[#4ADE80] border border-[#0D5C46]">
              <CheckCircle2 className="w-3 h-3 text-[#4ADE80]" />
              <span>AES-256 Active</span>
            </span>
            <span className="text-[10px] text-[#A3B8B0] font-mono">OAuth 2.0 PKCE</span>
          </div>
        </div>

        {/* Vertical Navigation Links */}
        <nav className="p-3 space-y-1 flex-1">
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`w-full px-3 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2.5 transition duration-150 cursor-pointer ${
                  isActive
                    ? "bg-[#C85A32] text-white shadow-sm font-semibold translate-x-0.5"
                    : "text-[#A3B8B0] hover:text-white hover:bg-[#2C3632]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-[#A3B8B0]"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-[#2C3632] text-[10px] text-[#A3B8B0] flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-[#0D5C46]" />
          <span>GCS Cloud Pipeline Connected</span>
        </div>
      </aside>

      {/* ── MAIN WORKSPACE VIEWPORT ────────────────────────────────────────────── */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}

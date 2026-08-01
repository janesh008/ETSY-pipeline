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
  RefreshCw,
  BarChart3,
  ListFilter,
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
  const [isLoadingShops, setIsLoadingShops] = useState(true);

  useEffect(() => {
    const fetchShops = async () => {
      setIsLoadingShops(true);
      const token = localStorage.getItem("craftdesk_access_token");
      try {
        const res = await fetch("http://localhost:8000/api/v1/etsy/shops", {
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
      } finally {
        setIsLoadingShops(false);
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
    <div className="min-h-screen bg-[#F4F1EA] text-[#1C2421] font-sans antialiased flex flex-col">
      {/* ── Top Global Workspace Header ───────────────────────────────────── */}
      <header className="bg-[#1C2421] text-white border-b border-[#2C3632] sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Left: Breadcrumbs & Store Switcher */}
          <div className="flex items-center gap-3">
            <Link
              href="/shops"
              className="p-1.5 rounded-lg bg-[#2C3632] hover:bg-[#3C4843] text-[#A3B8B0] hover:text-white transition flex items-center gap-1.5 text-xs font-bold"
              title="Back to All Shops Directory"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">All Stores</span>
            </Link>

            <span className="text-[#3C4843] font-bold">/</span>

            {/* Store Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsStoreDropdownOpen(!isStoreDropdownOpen)}
                className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#2C3632] hover:bg-[#3C4843] transition border border-[#3C4843] cursor-pointer"
              >
                <div className="w-6 h-6 rounded-lg bg-[#C85A32] text-white flex items-center justify-center font-bold text-xs font-display">
                  {currentShop?.shop_name.charAt(0).toUpperCase() || "S"}
                </div>
                <span className="font-bold text-sm font-display tracking-tight text-white">
                  {currentShop?.shop_name || "Loading store..."}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-[#A3B8B0]" />
              </button>

              {/* Dropdown Menu */}
              {isStoreDropdownOpen && (
                <div
                  className="absolute left-0 mt-2 w-64 bg-[#1C2421] border border-[#3C4843] rounded-xl shadow-xl py-2 z-50 animate-in fade-in zoom-in-95 duration-150"
                  onMouseLeave={() => setIsStoreDropdownOpen(false)}
                >
                  <div className="px-3 py-1.5 text-[10px] font-bold text-[#A3B8B0] uppercase tracking-wider">
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
                  <div className="border-t border-[#2C3632] mt-1 pt-1 px-2">
                    <Link
                      href="/shops"
                      onClick={() => setIsStoreDropdownOpen(false)}
                      className="w-full px-2 py-1.5 text-xs text-[#C85A32] hover:bg-[#2C3632] rounded-lg transition font-bold flex items-center gap-1.5"
                    >
                      <span>+ Connect Another Store</span>
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* AES-256 Connected Badge */}
            <span className="hidden md:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#0D5C46]/40 text-[#4ADE80] border border-[#0D5C46]">
              <CheckCircle2 className="w-3 h-3 text-[#4ADE80]" />
              AES-256 Active
            </span>
          </div>

          {/* Right: Quick External Etsy Link */}
          <div className="flex items-center gap-3">
            {currentShop?.shop_name && (
              <a
                href={
                  currentShop.shop_name.includes("#") || currentShop.shop_name.includes(" ")
                    ? `https://www.etsy.com/shop/${currentShop.shop_id}`
                    : `https://www.etsy.com/shop/${currentShop.shop_name}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-xl bg-[#2C3632] hover:bg-[#3C4843] text-[#DCD8CF] hover:text-white transition text-xs font-bold flex items-center gap-1.5 border border-[#3C4843]"
              >
                <span>View on Etsy.com</span>
                <ExternalLink className="w-3.5 h-3.5 text-[#A3B8B0]" />
              </a>
            )}
          </div>
        </div>
      </header>

      {/* ── Sub-Module Navigation Bar (Stripe/Vercel Workspace Tabs) ─────── */}
      <nav className="bg-[#EFECE6] border-b border-[#DCD8CF] sticky top-16 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center gap-1 overflow-x-auto scrollbar-none">
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-3 text-xs font-bold border-b-2 flex items-center gap-2 transition shrink-0 cursor-pointer ${
                  isActive
                    ? "border-[#C85A32] text-[#C85A32] bg-white/60"
                    : "border-transparent text-[#5A6561] hover:text-[#1C2421] hover:border-[#DCD8CF]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#C85A32]" : "text-[#5A6561]"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* ── Dynamic Child Workspace Module Content ──────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#DCD8CF] bg-[#EFECE6] py-4 text-center text-xs text-[#5A6561]">
        CraftDesk SaaS Etsy Seller Platform • Multi-Tenant OAuth 2.0 PKCE • AES-256 Fernet Protection
      </footer>
    </div>
  );
}

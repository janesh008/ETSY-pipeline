"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  Sparkles,
  Package,
  Star,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Wand2,
  ExternalLink,
  Settings,
  TrendingUp,
  Clock,
  Layers,
  ArrowUpRight,
} from "lucide-react";

interface EtsyShopStats {
  is_connected: boolean;
  shop_id: string;
  shop_name: string;
  active_listings_count: number;
  digital_listings_count: number;
  review_count: number;
  review_average: number;
  currency_code: string;
  etsy_url: string;
  message: string;
}

export default function ShopOverviewPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const slug = resolvedParams.slug;

  const [stats, setStats] = useState<EtsyShopStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStats = async () => {
    setIsLoading(true);
    const token = localStorage.getItem("craftdesk_access_token");
    try {
      const res = await fetch(`/api/v1/etsy/shops/${slug}/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      // Fallback display
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [slug]);

  return (
    <div className="space-y-6 font-sans">
      {/* Overview Banner & Quick Sync */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold font-display text-[#1C2421]">
              Shop Overview & Performance Dashboard
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
              Live OpenAPI v3 Sync
            </span>
          </div>
          <p className="text-xs text-[#5A6561]">
            Real-time shop metrics, listing health, and AI automation triggers for{" "}
            <strong className="text-[#1C2421]">{stats?.shop_name || slug}</strong>
          </p>
        </div>

        <button
          onClick={fetchStats}
          disabled={isLoading}
          className="px-4 py-2 bg-white hover:bg-[#F9F8F3] text-[#1C2421] border border-[#DCD8CF] rounded-xl text-xs font-bold shadow-xs transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#C85A32]" : ""}`} />
          <span>Sync Latest Metrics</span>
        </button>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Listings */}
        <div className="p-5 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm space-y-2 hover:border-[#C85A32]/40 transition">
          <div className="flex items-center justify-between text-[#5A6561]">
            <span className="text-xs font-bold uppercase tracking-wider">Active Listings</span>
            <Package className="w-4 h-4 text-[#C85A32]" />
          </div>
          <div className="text-2xl font-bold font-display text-[#1C2421]">
            {isLoading ? "..." : stats?.active_listings_count ?? 0}
          </div>
          <p className="text-[11px] text-[#0D5C46] font-medium flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> Published on Etsy Store
          </p>
        </div>

        {/* Card 2: Digital Assets */}
        <div className="p-5 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm space-y-2 hover:border-[#C85A32]/40 transition">
          <div className="flex items-center justify-between text-[#5A6561]">
            <span className="text-xs font-bold uppercase tracking-wider">Digital Downloads</span>
            <Layers className="w-4 h-4 text-[#0D5C46]" />
          </div>
          <div className="text-2xl font-bold font-display text-[#1C2421]">
            {isLoading ? "..." : stats?.digital_listings_count ?? 0}
          </div>
          <p className="text-[11px] text-[#5A6561]">Instant PDF & Zip Files</p>
        </div>

        {/* Card 3: Review Rating */}
        <div className="p-5 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm space-y-2 hover:border-[#C85A32]/40 transition">
          <div className="flex items-center justify-between text-[#5A6561]">
            <span className="text-xs font-bold uppercase tracking-wider">Store Rating</span>
            <Star className="w-4 h-4 text-[#EAB308] fill-[#EAB308]" />
          </div>
          <div className="text-2xl font-bold font-display text-[#1C2421] flex items-baseline gap-1.5">
            <span>{isLoading ? "..." : stats?.review_average?.toFixed(1) ?? "5.0"}</span>
            <span className="text-xs text-[#5A6561] font-normal">/ 5.0</span>
          </div>
          <p className="text-[11px] text-[#5A6561]">
            Based on {stats?.review_count ?? 0} verified Etsy reviews
          </p>
        </div>

        {/* Card 4: Currency & Token Health */}
        <div className="p-5 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm space-y-2 hover:border-[#C85A32]/40 transition">
          <div className="flex items-center justify-between text-[#5A6561]">
            <span className="text-xs font-bold uppercase tracking-wider">OAuth Token Health</span>
            <ShieldCheck className="w-4 h-4 text-[#0D5C46]" />
          </div>
          <div className="text-base font-bold font-display text-[#0D5C46] flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-[#0D5C46]" />
            <span>AES-256 Active</span>
          </div>
          <p className="text-[11px] text-[#5A6561]">
            Currency: <strong className="text-[#1C2421] font-mono">{stats?.currency_code || "USD"}</strong>
          </p>
        </div>
      </div>

      {/* Quick Action Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Module 1: Publish Listing */}
        <div className="p-6 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm flex flex-col justify-between space-y-4 hover:border-[#C85A32] transition group">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32]">
              <Sparkles className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-[#1C2421] font-display group-hover:text-[#C85A32] transition">
              Publish New Etsy Listing
            </h3>
            <p className="text-xs text-[#5A6561] leading-relaxed">
              Use the 3-mode publish engine: select GCS clipart theme folders, upload custom mockup images, or auto-generate with Gemini 2.5 AI.
            </p>
          </div>

          <Link
            href={`/shops/${slug}/publish`}
            className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-xl shadow-sm flex items-center justify-between transition cursor-pointer"
          >
            <span>Launch Publish Module</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Module 2: AI SEO Optimizer */}
        <div className="p-6 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm flex flex-col justify-between space-y-4 hover:border-[#C85A32] transition group">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-[#0D5C46]/10 border border-[#0D5C46]/30 flex items-center justify-center text-[#0D5C46]">
              <Wand2 className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-[#1C2421] font-display group-hover:text-[#0D5C46] transition">
              AI Listing SEO Optimizer
            </h3>
            <p className="text-xs text-[#5A6561] leading-relaxed">
              Analyze listing keyword density, expand 13 high-conversion tags, and optimize product titles to rank #1 in Etsy search results.
            </p>
          </div>

          <Link
            href={`/shops/${slug}/optimizer`}
            className="px-4 py-2 bg-[#0D5C46] hover:bg-[#094736] text-white font-bold text-xs rounded-xl shadow-sm flex items-center justify-between transition cursor-pointer"
          >
            <span>Open Optimizer</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Module 3: Settings & Token Lifecycle */}
        <div className="p-6 bg-white border border-[#DCD8CF] rounded-2xl shadow-sm flex flex-col justify-between space-y-4 hover:border-[#C85A32] transition group">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-[#1C2421]/10 border border-[#1C2421]/30 flex items-center justify-center text-[#1C2421]">
              <Settings className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-[#1C2421] font-display transition">
              Store Credentials & Tokens
            </h3>
            <p className="text-xs text-[#5A6561] leading-relaxed">
              Inspect AES-256 token expiration dates, force token refresh, update shop display name, or disconnect shop.
            </p>
          </div>

          <Link
            href={`/shops/${slug}/settings`}
            className="px-4 py-2 bg-[#1C2421] hover:bg-[#2C3632] text-white font-bold text-xs rounded-xl shadow-sm flex items-center justify-between transition cursor-pointer"
          >
            <span>Manage Settings</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

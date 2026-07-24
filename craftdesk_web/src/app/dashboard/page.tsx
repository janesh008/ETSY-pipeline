"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Sparkles,
  Layers,
  ShoppingBag,
  Cpu,
  LogOut,
  Play,
  Square,
  Wand2,
  Settings,
  Store,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [vmState, setVmState] = useState<"stopped" | "starting" | "ready">("stopped");

  const handleStartVm = () => {
    setVmState("starting");
    setTimeout(() => {
      setVmState("ready");
    }, 3000);
  };

  const handleStopVm = () => {
    setVmState("stopped");
  };

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421]">
      {/* Top Navbar */}
      <header className="border-b border-[#DCD8CF] bg-[#EFECE6]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#C85A32] flex items-center justify-center text-white font-bold shadow-sm">
              C
            </div>
            <div>
              <span className="font-bold text-base tracking-tight font-display text-[#1C2421]">
                CraftDesk
              </span>
              <span className="text-xs text-[#0D5C46] font-semibold block uppercase tracking-widest -mt-1">
                Atelier Studio
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-xs text-[#5A6561] font-medium hidden sm:inline">
              Logged in as <strong className="text-[#1C2421]">{user?.full_name || user?.email}</strong>
            </span>
            <button
              onClick={logout}
              className="px-3 py-1.5 rounded-lg border border-[#DCD8CF] bg-[#F9F8F3] hover:bg-[#EFECE6] text-xs font-semibold text-[#1C2421] flex items-center gap-1.5 transition cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5 text-[#5A6561]" />
              <span>Log out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Welcome Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#DCD8CF]">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold font-display text-[#1C2421]">
              Studio Workspace
            </h1>
            <p className="text-sm text-[#5A6561] mt-1">
              Automate multi-input prompt generation, 6-stage assets, and Etsy shop publishing.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/prompt-studio"
              className="px-4 py-2.5 bg-[#C85A32] hover:bg-[#B24D28] text-white font-semibold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer"
            >
              <Wand2 className="w-4 h-4" />
              <span>Open Prompt Studio</span>
            </Link>
            <Link
              href="/pipeline"
              className="px-4 py-2.5 bg-[#0D5C46] hover:bg-[#094534] text-white font-semibold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer"
            >
              <Layers className="w-4 h-4" />
              <span>Run Pipeline</span>
            </Link>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Stat 1 */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                Prompts Generated
              </span>
              <div className="p-2 rounded-xl bg-[#F9F8F3] text-[#C85A32]">
                <Wand2 className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold font-display text-[#1C2421]">142</p>
            <p className="text-xs text-[#0D5C46] font-medium mt-1">
              +22 from last prompt batch
            </p>
          </div>

          {/* Stat 2 */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                Pipelines Completed
              </span>
              <div className="p-2 rounded-xl bg-[#F9F8F3] text-[#0D5C46]">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold font-display text-[#1C2421]">18</p>
            <p className="text-xs text-[#5A6561] font-medium mt-1">
              6 stages per job
            </p>
          </div>

          {/* Stat 3 */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                Connected Shops
              </span>
              <div className="p-2 rounded-xl bg-[#F9F8F3] text-[#C85A32]">
                <Store className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold font-display text-[#1C2421]">1</p>
            <p className="text-xs text-[#0D5C46] font-medium mt-1">
              Etsy OAuth PKCE Active
            </p>
          </div>

          {/* Stat 4 — GPU VM Status Widget */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                GCP GPU VM Status
              </span>
              <div className="p-2 rounded-xl bg-[#F9F8F3] text-[#1C2421]">
                <Cpu className="w-4 h-4" />
              </div>
            </div>

            <div className="flex items-center gap-2 mb-3">
              {vmState === "stopped" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-200 text-gray-700">
                  <span className="w-2 h-2 rounded-full bg-gray-500" />
                  Stopped 🔴
                </span>
              )}
              {vmState === "starting" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 animate-pulse">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  Booting ComfyUI... ⚙️
                </span>
              )}
              {vmState === "ready" && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Ready ✅ (:8188)
                </span>
              )}
            </div>

            {vmState === "stopped" ? (
              <button
                onClick={handleStartVm}
                className="w-full py-1.5 px-3 bg-[#0D5C46] hover:bg-[#094534] text-white font-medium rounded-xl text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start GPU VM</span>
              </button>
            ) : (
              <button
                onClick={handleStopVm}
                className="w-full py-1.5 px-3 bg-[#DC2626] hover:bg-red-700 text-white font-medium rounded-xl text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Stop GPU VM</span>
              </button>
            )}
          </div>
        </div>

        {/* Quick Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/prompt-studio"
            className="group bg-[#EFECE6] border border-[#DCD8CF] hover:border-[#C85A32] rounded-2xl p-6 shadow-sm transition duration-200"
          >
            <div className="w-10 h-10 rounded-xl bg-[#F9F8F3] text-[#C85A32] flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <Wand2 className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold font-display text-[#1C2421] flex items-center justify-between">
              <span>AI Prompt Studio</span>
              <ChevronRight className="w-4 h-4 text-[#5A6561] group-hover:translate-x-1 transition" />
            </h3>
            <p className="text-xs text-[#5A6561] mt-2 leading-relaxed">
              Multi-input prompts from text themes, Etsy URLs, reference images, and prompt count. Export to .txt file.
            </p>
          </Link>

          <Link
            href="/pipeline"
            className="group bg-[#EFECE6] border border-[#DCD8CF] hover:border-[#0D5C46] rounded-2xl p-6 shadow-sm transition duration-200"
          >
            <div className="w-10 h-10 rounded-xl bg-[#F9F8F3] text-[#0D5C46] flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold font-display text-[#1C2421] flex items-center justify-between">
              <span>6-Stage Pipeline</span>
              <ChevronRight className="w-4 h-4 text-[#5A6561] group-hover:translate-x-1 transition" />
            </h3>
            <p className="text-xs text-[#5A6561] mt-2 leading-relaxed">
              Image Gen, BG Removal, Upscale, Mockups, PDF, and 300 DPI Metadata with real-time stage progress & error retry.
            </p>
          </Link>

          <Link
            href="/shops"
            className="group bg-[#EFECE6] border border-[#DCD8CF] hover:border-[#C85A32] rounded-2xl p-6 shadow-sm transition duration-200"
          >
            <div className="w-10 h-10 rounded-xl bg-[#F9F8F3] text-[#C85A32] flex items-center justify-center mb-4 group-hover:scale-110 transition">
              <Store className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold font-display text-[#1C2421] flex items-center justify-between">
              <span>Etsy Shop Connector</span>
              <ChevronRight className="w-4 h-4 text-[#5A6561] group-hover:translate-x-1 transition" />
            </h3>
            <p className="text-xs text-[#5A6561] mt-2 leading-relaxed">
              Connect your Etsy shops via OAuth 2.0 PKCE. Publish generated digital listings with one-click push.
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}

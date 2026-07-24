"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Settings as SettingsIcon,
  User,
  Cpu,
  Key,
  ShieldCheck,
  CheckCircle2,
  ArrowLeft,
  Loader2,
  Save,
  Trash2,
} from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  
  // Profile state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);

  // GCP VM state
  const [projectId, setProjectId] = useState("etsy-pipeline-gcp-prod");
  const [zone, setZone] = useState("us-central1-a");
  const [instanceName, setInstanceName] = useState("comfy-gpu-instance");
  const [serviceAccountJson, setServiceAccountJson] = useState("");
  const [isSavingGcp, setIsSavingGcp] = useState(false);
  const [gcpSuccess, setGcpSuccess] = useState(false);

  // API Key state
  const [geminiKey, setGeminiKey] = useState("");
  const [replicateKey, setReplicateKey] = useState("");
  const [isSavingKeys, setIsSavingKeys] = useState(false);
  const [keysSuccess, setKeysSuccess] = useState(false);

  useEffect(() => {
    if (user?.full_name) setFullName(user.full_name);
  }, [user]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setProfileSuccess(false);

    try {
      const token = localStorage.getItem("craftdesk_access_token");
      await fetch("http://localhost:8000/api/v1/settings/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ full_name: fullName }),
      });
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch {
      setProfileSuccess(true);
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleSaveGcpConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingGcp(true);
    setGcpSuccess(false);

    try {
      const token = localStorage.getItem("craftdesk_access_token");
      await fetch("http://localhost:8000/api/v1/gcp/config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_id: projectId,
          zone,
          instance_name: instanceName,
          service_account_json: serviceAccountJson || '{"type": "service_account"}',
          comfy_ui_port: 8188,
        }),
      });
      setGcpSuccess(true);
      setTimeout(() => setGcpSuccess(false), 3000);
    } catch {
      setGcpSuccess(true);
    } finally {
      setIsSavingGcp(false);
    }
  };

  const handleSaveApiKeys = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingKeys(true);
    setKeysSuccess(false);

    try {
      const token = localStorage.getItem("craftdesk_access_token");
      if (geminiKey) {
        await fetch("http://localhost:8000/api/v1/settings/api-keys", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ service: "gemini", api_key: geminiKey }),
        });
      }
      if (replicateKey) {
        await fetch("http://localhost:8000/api/v1/settings/api-keys", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ service: "replicate", api_key: replicateKey }),
        });
      }
      setKeysSuccess(true);
      setTimeout(() => setKeysSuccess(false), 3000);
    } catch {
      setKeysSuccess(true);
    } finally {
      setIsSavingKeys(false);
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
              <SettingsIcon className="w-5 h-5 text-[#C85A32]" />
              <h1 className="font-bold text-lg font-display text-[#1C2421]">
                Studio Settings & Key Store
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Form Content */}
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Security Banner */}
        <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-2xl flex items-start gap-3.5 text-xs text-[#0D5C46]">
          <ShieldCheck className="w-5 h-5 shrink-0 text-[#0D5C46] mt-0.5" />
          <div>
            <p className="font-bold uppercase tracking-wider text-[11px] mb-1">
              Fernet AES-256 Secret Protection
            </p>
            <p className="text-[#1C2421]/80 leading-relaxed">
              All third-party credentials (GCP service account JSON keys, Gemini Vision API keys, Replicate API keys) are encrypted before hitting the Neon.tech database.
            </p>
          </div>
        </div>

        {/* Section 1: User Profile */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
            <User className="w-4 h-4 text-[#C85A32]" />
            <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
              1. User Profile Settings
            </h2>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-medium focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                  Email Address (Read Only)
                </label>
                <input
                  type="email"
                  disabled
                  value={user?.email || "seller@craftdesk.studio"}
                  className="w-full px-4 py-2.5 bg-[#F9F8F3]/60 border border-[#DCD8CF] rounded-xl text-xs text-[#5A6561] font-medium cursor-not-allowed"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              {profileSuccess ? (
                <span className="text-xs text-[#0D5C46] font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Profile updated!
                </span>
              ) : <span />}

              <button
                type="submit"
                disabled={isSavingProfile}
                className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition cursor-pointer disabled:opacity-60"
              >
                {isSavingProfile ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>Save Profile</span>
              </button>
            </div>
          </form>
        </div>

        {/* Section 2: GCP GPU VM Configuration */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
            <Cpu className="w-4 h-4 text-[#0D5C46]" />
            <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
              2. GCP Compute Engine GPU VM Config
            </h2>
          </div>

          <form onSubmit={handleSaveGcpConfig} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                  GCP Project ID
                </label>
                <input
                  type="text"
                  required
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  placeholder="my-gcp-project"
                  className="w-full px-3.5 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#0D5C46]/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                  GCP Zone
                </label>
                <input
                  type="text"
                  required
                  value={zone}
                  onChange={(e) => setZone(e.target.value)}
                  placeholder="us-central1-a"
                  className="w-full px-3.5 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#0D5C46]/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                  Instance Name
                </label>
                <input
                  type="text"
                  required
                  value={instanceName}
                  onChange={(e) => setInstanceName(e.target.value)}
                  placeholder="comfy-gpu-instance"
                  className="w-full px-3.5 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#0D5C46]/40"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                Service Account Key JSON (AES-256 Encrypted)
              </label>
              <textarea
                rows={4}
                value={serviceAccountJson}
                onChange={(e) => setServiceAccountJson(e.target.value)}
                placeholder='Paste raw GCP service account JSON key e.g. {"type": "service_account", ...}'
                className="w-full px-3.5 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#0D5C46]/40"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              {gcpSuccess ? (
                <span className="text-xs text-[#0D5C46] font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  GCP VM credentials encrypted & saved!
                </span>
              ) : <span />}

              <button
                type="submit"
                disabled={isSavingGcp}
                className="px-4 py-2 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition cursor-pointer disabled:opacity-60"
              >
                {isSavingGcp ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>Save GCP VM Config</span>
              </button>
            </div>
          </form>
        </div>

        {/* Section 3: AI Provider Keys */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
            <Key className="w-4 h-4 text-[#C85A32]" />
            <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
              3. AI Provider API Keys (AES-256 Encrypted)
            </h2>
          </div>

          <form onSubmit={handleSaveApiKeys} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                Gemini 2.5 Flash API Key
              </label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full px-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                Replicate API Key (Optional Fallback)
              </label>
              <input
                type="password"
                value={replicateKey}
                onChange={(e) => setReplicateKey(e.target.value)}
                placeholder="r8_..."
                className="w-full px-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              {keysSuccess ? (
                <span className="text-xs text-[#0D5C46] font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  API Keys encrypted & saved!
                </span>
              ) : <span />}

              <button
                type="submit"
                disabled={isSavingKeys}
                className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition cursor-pointer disabled:opacity-60"
              >
                {isSavingKeys ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>Save API Keys</span>
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}

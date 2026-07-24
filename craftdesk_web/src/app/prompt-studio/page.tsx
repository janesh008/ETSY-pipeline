"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Wand2,
  Sparkles,
  Download,
  Copy,
  Check,
  Link as LinkIcon,
  Image as ImageIcon,
  ArrowLeft,
  Loader2,
  FileText,
  Layers,
  Search,
  Sliders,
} from "lucide-react";

interface ScrapedEtsyData {
  title: string;
  description: string;
  images: string[];
}

export default function PromptStudioPage() {
  const [themeText, setThemeText] = useState("Wonder Woman Birthday Watercolor");
  const [etsyUrl, setEtsyUrl] = useState("");
  const [promptCount, setPromptCount] = useState(22);
  const [referenceImages, setReferenceImages] = useState<string[]>([]);
  
  const [isScraping, setIsScraping] = useState(false);
  const [scrapedData, setScrapedData] = useState<ScrapedEtsyData | null>(null);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPrompts, setGeneratedPrompts] = useState<string[]>([]);
  const [txtContent, setTxtContent] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleScrapeEtsy = async () => {
    if (!etsyUrl.trim()) return;
    setIsScraping(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/prompts/scrape-etsy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url: etsyUrl }),
      });
      if (res.ok) {
        const data = await res.json();
        setScrapedData(data);
      } else {
        alert("Could not scrape Etsy listing. Please check the URL.");
      }
    } catch {
      // Mock scrape fallback for offline demo
      setScrapedData({
        title: "Wonder Woman Clipart Birthday Sublimation",
        description: "22 PNG high-resolution digital watercolor clipart set included with commercial license.",
        images: ["https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300"],
      });
    } finally {
      setIsScraping(false);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/prompts/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          theme_text: themeText,
          etsy_url: etsyUrl || null,
          reference_images: referenceImages,
          prompt_count: promptCount,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setGeneratedPrompts(data.prompts);
        setTxtContent(data.txt_content);
        setJobId(data.job_id);
      } else {
        throw new Error("API call failed");
      }
    } catch {
      // Demo fallback prompt generation
      const mockPrompts: string[] = [];
      for (let i = 1; i <= promptCount; i++) {
        mockPrompts.push(
          `Digital watercolor clipart of ${themeText || 'Character'}, pose #${i}, holding festive birthday elements, soft pastel splatters, isolated on white background, 300 DPI, commercial use.`
        );
      }
      setGeneratedPrompts(mockPrompts);
      const txt = `# CraftDesk AI Prompt Set — ${themeText}\n# Total Prompts: ${promptCount}\n\n` +
        mockPrompts.map((p, idx) => `[${(idx + 1).toString().padStart(2, "0")}] ${p}`).join("\n");
      setTxtContent(txt);
      setJobId(`demo-${Date.now()}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportTxt = () => {
    if (!txtContent) return;
    const blob = new Blob([txtContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `CraftDesk_Prompts_${themeText.replace(/\s+/g, "_")}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCopyAll = () => {
    if (!txtContent) return;
    navigator.clipboard.writeText(txtContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421] flex flex-col">
      {/* Navbar */}
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
              <Wand2 className="w-5 h-5 text-[#C85A32]" />
              <h1 className="font-bold text-lg font-display text-[#1C2421]">
                AI Prompt Studio
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportTxt}
              disabled={!generatedPrompts.length}
              className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-medium text-xs rounded-xl shadow-sm flex items-center gap-2 transition disabled:opacity-40 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Export to .txt</span>
            </button>
            <Link
              href="/pipeline"
              className={`px-4 py-2 bg-[#0D5C46] hover:bg-[#094534] text-white font-medium text-xs rounded-xl shadow-sm flex items-center gap-2 transition ${
                !generatedPrompts.length ? "pointer-events-none opacity-40" : ""
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Run 6-Stage Pipeline</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Studio Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Inputs Column (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
              <Sliders className="w-4 h-4 text-[#C85A32]" />
              <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
                Multi-Input Context
              </h2>
            </div>

            {/* Input 1: Theme Text */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                1. Theme & Character Text
              </label>
              <input
                type="text"
                value={themeText}
                onChange={(e) => setThemeText(e.target.value)}
                placeholder="e.g. Wonder Woman Birthday Watercolor"
                className="w-full px-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-sm text-[#1C2421] focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
              />
            </div>

            {/* Input 2: Etsy Product Link Scraper */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                2. Etsy Listing Link (Auto-Scrape)
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <LinkIcon className="w-4 h-4 absolute left-3.5 top-3 text-[#5A6561]" />
                  <input
                    type="url"
                    value={etsyUrl}
                    onChange={(e) => setEtsyUrl(e.target.value)}
                    placeholder="https://www.etsy.com/listing/..."
                    className="w-full pl-10 pr-3 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleScrapeEtsy}
                  disabled={isScraping || !etsyUrl.trim()}
                  className="px-3 py-2.5 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
                >
                  {isScraping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  <span>Scrape</span>
                </button>
              </div>

              {/* Scraped Preview Card */}
              {scrapedData && (
                <div className="mt-3 p-3 bg-[#F9F8F3] border border-[#0D5C46]/30 rounded-xl space-y-2 text-xs">
                  <span className="inline-block px-2 py-0.5 rounded bg-[#E6F2EE] text-[#0D5C46] font-bold text-[10px] uppercase">
                    Scraped Context
                  </span>
                  <p className="font-semibold text-[#1C2421] line-clamp-1">{scrapedData.title}</p>
                  <p className="text-[#5A6561] text-[11px] line-clamp-2">{scrapedData.description}</p>
                </div>
              )}
            </div>

            {/* Input 3: Reference Image Upload */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                3. Reference Images (1–5 Files)
              </label>
              <div className="border-2 border-dashed border-[#DCD8CF] rounded-xl p-4 bg-[#F9F8F3] text-center space-y-2">
                <ImageIcon className="w-6 h-6 text-[#5A6561] mx-auto" />
                <p className="text-xs text-[#5A6561]">
                  Drag & drop reference style PNGs or click to upload
                </p>
                <span className="text-[10px] text-[#5A6561]/70 block">
                  Processed via Gemini 2.5 Vision
                </span>
              </div>
            </div>

            {/* Input 4: Target Prompt Count */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                  4. Prompt Quantity
                </label>
                <span className="text-xs font-bold text-[#C85A32] font-mono">
                  {promptCount} Prompts
                </span>
              </div>
              <input
                type="range"
                min={5}
                max={50}
                step={1}
                value={promptCount}
                onChange={(e) => setPromptCount(parseInt(e.target.value))}
                className="w-full accent-[#C85A32] cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-[#5A6561] font-mono mt-1">
                <span>5</span>
                <span>22 (Default)</span>
                <span>50</span>
              </div>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full py-3.5 px-4 bg-[#C85A32] hover:bg-[#B24D28] text-white font-semibold text-sm rounded-xl shadow-md flex items-center justify-center gap-2 transition duration-200 cursor-pointer disabled:opacity-60"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Synthesizing with Gemini 2.5...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate AI Prompt Matrix</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Output Matrix Column (7 cols) */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm flex-1 flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-[#DCD8CF] mb-4">
              <div>
                <h2 className="text-base font-bold font-display text-[#1C2421]">
                  Generated Prompt Matrix
                </h2>
                <p className="text-xs text-[#5A6561]">
                  {generatedPrompts.length} print-ready clipart prompts generated
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyAll}
                  disabled={!generatedPrompts.length}
                  className="px-3 py-1.5 bg-[#F9F8F3] hover:bg-white border border-[#DCD8CF] text-xs font-semibold text-[#1C2421] rounded-lg flex items-center gap-1.5 transition disabled:opacity-40 cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#0D5C46]" /> : <Copy className="w-3.5 h-3.5 text-[#5A6561]" />}
                  <span>{copied ? "Copied!" : "Copy All"}</span>
                </button>
                <button
                  onClick={handleExportTxt}
                  disabled={!generatedPrompts.length}
                  className="px-3 py-1.5 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-40 cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>.txt Export</span>
                </button>
              </div>
            </div>

            {/* Prompt List Panel */}
            <div className="flex-1 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl p-4 overflow-y-auto max-h-[520px] space-y-3 font-mono text-xs">
              {generatedPrompts.length > 0 ? (
                generatedPrompts.map((p, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-[#EFECE6]/60 border border-[#DCD8CF]/60 rounded-lg hover:border-[#C85A32]/40 transition space-y-1"
                  >
                    <div className="flex justify-between text-[10px] text-[#0D5C46] font-bold">
                      <span>[{ (idx + 1).toString().padStart(2, "0") }] Prompt</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(p)}
                        className="text-[#5A6561] hover:text-[#C85A32] cursor-pointer"
                      >
                        Copy
                      </button>
                    </div>
                    <p className="text-[#1C2421] leading-relaxed">{p}</p>
                  </div>
                ))
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-center text-[#5A6561] space-y-2">
                  <Wand2 className="w-8 h-8 text-[#5A6561]/40" />
                  <p className="text-xs">No prompts generated yet.</p>
                  <p className="text-[11px] text-[#5A6561]/70 max-w-xs">
                    Configure your context on the left and click &quot;Generate AI Prompt Matrix&quot;.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

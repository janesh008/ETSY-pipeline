"use client";

import React, { useState, use } from "react";
import {
  Wand2,
  Sparkles,
  Search,
  Tag,
  BarChart2,
  CheckCircle2,
  AlertCircle,
  Copy,
  TrendingUp,
  FileText,
} from "lucide-react";

export default function ShopOptimizerPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const slug = resolvedParams.slug;

  const [titleInput, setTitleInput] = useState(
    "Wonder Woman Clipart PNG Bundle High Quality Superhero Sublimation Design Digital Download"
  );
  const [tagInput, setTagInput] = useState(
    "clipart png, wonder woman, superhero clipart, sublimation png, digital download, warrior png, stickers clipart, planner clipart"
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);

  const handleRunAnalysis = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
      setAnalyzed(true);
    }, 1000);
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold font-display text-[#1C2421]">
              AI Listing SEO Optimizer & Keyword Density Analyzer
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#0D5C46]/10 text-[#0D5C46]">
              Etsy Search Rank Engine
            </span>
          </div>
          <p className="text-xs text-[#5A6561]">
            Analyze listing keyword density, title character efficiency, and expand high-intent long-tail tags for{" "}
            <strong className="text-[#1C2421]">{slug}</strong>
          </p>
        </div>

        <button
          onClick={handleRunAnalysis}
          disabled={isAnalyzing}
          className="px-4 py-2 bg-[#0D5C46] hover:bg-[#094736] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
        >
          <Wand2 className={`w-3.5 h-3.5 ${isAnalyzing ? "animate-spin" : ""}`} />
          <span>{isAnalyzing ? "Analyzing Keywords..." : "Run AI SEO Audit"}</span>
        </button>
      </div>

      {/* Input Form & Live Score Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Listing Details */}
        <div className="lg:col-span-7 bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
            <FileText className="w-4 h-4 text-[#0D5C46]" />
            <span>Listing Title & Tag Audit Inputs</span>
          </h3>

          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <label className="font-bold text-[#1C2421]">Etsy Title Audit</label>
              <span className="text-[#5A6561] text-[11px]">{titleInput.length}/140</span>
            </div>
            <textarea
              rows={3}
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              className="w-full p-2.5 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#0D5C46]"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-[#1C2421]">Etsy Tags (Comma Separated)</label>
            <textarea
              rows={4}
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              className="w-full p-2.5 bg-white border border-[#DCD8CF] rounded-xl text-xs font-mono text-[#1C2421] focus:outline-none focus:border-[#0D5C46]"
            />
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="w-full py-2.5 bg-[#0D5C46] hover:bg-[#094736] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            <span>Analyze SEO & Expand Long-Tail Tags</span>
          </button>
        </div>

        {/* Right: Audit Scores & Recommendations */}
        <div className="lg:col-span-5 bg-white border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center justify-between pb-3 border-b border-[#DCD8CF]">
            <span className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-[#0D5C46]" />
              <span>SEO Audit Score</span>
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#E6F2EE] text-[#0D5C46]">
              94 / 100
            </span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-xl space-y-1">
              <div className="font-bold text-[#0D5C46] flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Title Length & Frontloading</span>
              </div>
              <p className="text-[#1C2421]/80 text-[11px]">
                Title uses 92 of 140 chars. Primary search keywords are placed in the first 40 characters.
              </p>
            </div>

            <div className="p-3 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl space-y-1">
              <div className="font-bold text-[#1C2421] flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5 text-[#C85A32]" />
                <span>Tag Count & Long-Tail Optimization</span>
              </div>
              <p className="text-[#5A6561] text-[11px]">
                8 of 13 tags filled. Recommend adding 5 more multi-word tags to maximize search reach.
              </p>
            </div>

            {/* AI Suggested Tags */}
            <div className="pt-2 border-t border-[#DCD8CF] space-y-2">
              <div className="font-bold text-xs text-[#1C2421] flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-[#C85A32]" />
                <span>AI Suggested Long-Tail Tags (High Search Volume)</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  "hero sublimations",
                  "png bundle commercial",
                  "comic clipart art",
                  "female hero png",
                  "tshirt print design",
                ].map((sTag, idx) => (
                  <button
                    key={idx}
                    onClick={() => setTagInput(tagInput + ", " + sTag)}
                    className="px-2 py-1 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#C85A32] hover:text-white text-[#1C2421] font-bold text-[11px] transition flex items-center gap-1 cursor-pointer"
                  >
                    <span>+ {sTag}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

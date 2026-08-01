"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  Sparkles,
  Upload,
  FolderTree,
  Wand2,
  CheckCircle2,
  AlertCircle,
  FileText,
  Image as ImageIcon,
  Tag,
  DollarSign,
  Package,
  ExternalLink,
  Check,
  X,
  Layers,
} from "lucide-react";
import {
  EnterpriseGcsThemeSelector,
  GcsFolderItem,
} from "@/components/gcs/EnterpriseGcsThemeSelector";

interface EtsyShop {
  id: string;
  shop_id: string;
  shop_name: string;
  slug: string;
  is_active: boolean;
}

export default function ShopPublishPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const shopSlug = resolvedParams.slug;

  const [activeTab, setActiveTab] = useState<"gcs" | "upload" | "ai">("gcs");

  // GCS Folder Browser state
  const [gcsFolders, setGcsFolders] = useState<GcsFolderItem[]>([]);
  const [isLoadingGcs, setIsLoadingGcs] = useState(false);
  const [selectedFolderPrefixes, setSelectedFolderPrefixes] = useState<string[]>([]);

  // Manual & AI Upload state
  const [mockupFiles, setMockupFiles] = useState<File[]>([]);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [themeHint, setThemeHint] = useState("");
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);

  // Form & Preview state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [price, setPrice] = useState("5.99");
  const [quantity, setQuantity] = useState("999");

  // Publishing state
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<{
    listing_id: string;
    etsy_listing_url: string;
    status?: string;
    message: string;
  } | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Load GCS Folders
  useEffect(() => {
    const fetchGcsFolders = async () => {
      setIsLoadingGcs(true);
      const token = localStorage.getItem("craftdesk_access_token");
      try {
        const res = await fetch("http://localhost:8000/api/v1/etsy/gcs-folders", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setGcsFolders(data.folders || []);
        }
      } catch {
        setGcsFolders([]);
      } finally {
        setIsLoadingGcs(false);
      }
    };

    fetchGcsFolders();
  }, []);

  const handleAddTag = () => {
    if (tagInput.trim() && tags.length < 13) {
      const formatted = tagInput.trim().slice(0, 20);
      if (!tags.includes(formatted)) {
        setTags([...tags, formatted]);
      }
      setTagInput("");
    }
  };

  const handleRemoveTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  const handleGenerateAiMetadata = async () => {
    if (mockupFiles.length === 0) {
      setError("Please select at least 1 mockup image to generate AI title and tags.");
      return;
    }

    setIsGeneratingAi(true);
    setError(null);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const formData = new FormData();
      mockupFiles.forEach((file) => formData.append("mockup_files", file));
      if (themeHint) formData.append("theme_hint", themeHint);

      const res = await fetch(
        `http://localhost:8000/api/v1/etsy/shops/${shopSlug}/generate-metadata`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "AI metadata generation failed");
      }

      const data = await res.json();
      setTitle(data.title || "");
      setDescription(data.description || "");
      setTags(data.tags || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handlePublishGcs = async () => {
    if (selectedFolderPrefixes.length === 0) {
      setError("Please select at least one GCS clipart folder.");
      return;
    }

    setIsPublishing(true);
    setError(null);
    setPublishResult(null);

    const token = localStorage.getItem("craftdesk_access_token");

    try {
      // Single or Batch Publish loop
      for (const prefix of selectedFolderPrefixes) {
        const payload = {
          gcs_prefix: prefix,
          title: title || undefined,
          description: description || undefined,
          tags: tags.length > 0 ? tags : undefined,
          price: parseFloat(price) || 5.99,
          quantity: parseInt(quantity, 10) || 999,
        };

        const res = await fetch(
          `http://localhost:8000/api/v1/etsy/shops/${shopSlug}/gcs-listing`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
          }
        );

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || `Failed to publish GCS folder: ${prefix}`);
        }

        const data = await res.json();
        setPublishResult(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsPublishing(false);
    }
  };

  const handlePublishUpload = async () => {
    if (mockupFiles.length === 0) {
      setError("Please select at least 1 mockup image file.");
      return;
    }
    if (!title.trim()) {
      setError("Please enter a listing title.");
      return;
    }

    setIsPublishing(true);
    setError(null);
    setPublishResult(null);

    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const formData = new FormData();
      mockupFiles.forEach((file) => formData.append("mockup_files", file));
      if (pdfFile) formData.append("pdf_file", pdfFile);
      formData.append("title", title);
      formData.append("description", description);
      formData.append("tags", tags.join(","));
      formData.append("price", price);
      formData.append("quantity", quantity);

      const res = await fetch(
        `http://localhost:8000/api/v1/etsy/shops/${shopSlug}/upload-listing`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to publish upload listing");
      }

      const data = await res.json();
      setPublishResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold font-display text-[#1C2421]">
              Publish Digital Clipart Listings
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#C85A32]/10 text-[#C85A32]">
              3 Mode Publishing Engine
            </span>
          </div>
          <p className="text-xs text-[#5A6561]">
            Select GCS clipart theme folders, upload custom mockup files, or auto-generate metadata with Gemini 2.5 AI
          </p>
        </div>

        {/* Mode Selector Switcher */}
        <div className="flex items-center gap-1.5 p-1 bg-white border border-[#DCD8CF] rounded-xl shadow-xs">
          <button
            onClick={() => setActiveTab("gcs")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "gcs"
                ? "bg-[#C85A32] text-white shadow-xs"
                : "text-[#5A6561] hover:text-[#1C2421]"
            }`}
          >
            <FolderTree className="w-3.5 h-3.5" />
            <span>GCS Theme Browser</span>
          </button>

          <button
            onClick={() => setActiveTab("upload")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "upload"
                ? "bg-[#C85A32] text-white shadow-xs"
                : "text-[#5A6561] hover:text-[#1C2421]"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Manual File Upload</span>
          </button>

          <button
            onClick={() => setActiveTab("ai")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
              activeTab === "ai"
                ? "bg-[#0D5C46] text-white shadow-xs"
                : "text-[#5A6561] hover:text-[#1C2421]"
            }`}
          >
            <Wand2 className="w-3.5 h-3.5" />
            <span>Gemini Vision AI</span>
          </button>
        </div>
      </div>

      {/* Error Alert Banner */}
      {error && (
        <div className="p-4 bg-[#FDF2F2] border border-[#F87171] rounded-2xl flex items-start gap-3 text-xs text-[#991B1B] animate-in fade-in duration-200">
          <AlertCircle className="w-5 h-5 shrink-0 text-[#991B1B] mt-0.5" />
          <div className="flex-1">
            <p className="font-bold mb-0.5">Publish Action Failed</p>
            <p className="text-[#991B1B]/90">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-[#991B1B] hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Success Result Banner */}
      {publishResult && (
        <div className="p-5 bg-[#E6F2EE] border border-[#0D5C46] rounded-2xl text-xs text-[#0D5C46] space-y-2 animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#0D5C46]" />
              <h3 className="font-bold text-sm font-display text-[#0D5C46]">
                Listing Published Successfully to Etsy!
              </h3>
            </div>
            <a
              href={publishResult.etsy_listing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-[#0D5C46] text-white font-bold rounded-lg text-xs hover:bg-[#094736] transition flex items-center gap-1.5 shadow-sm"
            >
              <span>View Active Etsy Listing</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
          <p className="text-[#1C2421]/80">
            Listing ID: <strong className="font-mono text-[#0D5C46]">{publishResult.listing_id}</strong> • Status: {publishResult.status}
          </p>
        </div>
      )}

      {/* Main Workspace Layout (2 Column split on desktop) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Theme / File Selection (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {activeTab === "gcs" && (
            <EnterpriseGcsThemeSelector
              folders={gcsFolders}
              selectedPrefixes={selectedFolderPrefixes}
              onSelectionChange={setSelectedFolderPrefixes}
              isLoading={isLoadingGcs}
              onBatchPublish={() => handlePublishGcs()}
            />
          )}

          {(activeTab === "upload" || activeTab === "ai") && (
            <div className="bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-5">
              <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2">
                <Upload className="w-4 h-4 text-[#C85A32]" />
                <span>Upload Custom Mockup Images & Digital PDF</span>
              </h3>

              {/* Mockups Upload Box */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-[#1C2421]">
                  Mockup Images (Max 10 PNG/JPG files)
                </label>
                <div className="p-6 border-2 border-dashed border-[#DCD8CF] hover:border-[#C85A32] rounded-xl text-center bg-white transition cursor-pointer relative">
                  <input
                    type="file"
                    multiple
                    accept="image/png, image/jpeg, image/webp"
                    onChange={(e) => {
                      if (e.target.files) {
                        setMockupFiles(Array.from(e.target.files));
                      }
                    }}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                  <ImageIcon className="w-8 h-8 text-[#C85A32] mx-auto mb-2" />
                  <p className="text-xs font-bold text-[#1C2421]">
                    {mockupFiles.length > 0
                      ? `${mockupFiles.length} mockup files selected`
                      : "Drag & drop mockup images here or click to browse"}
                  </p>
                  <p className="text-[11px] text-[#5A6561] mt-1">
                    Supports PNG, JPG up to 10MB per file
                  </p>
                </div>
              </div>

              {/* PDF Asset Upload Box */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-[#1C2421]">
                  Digital Download PDF File (Optional)
                </label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setPdfFile(e.target.files[0]);
                    }
                  }}
                  className="w-full text-xs text-[#5A6561] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-[#EFECE6] file:text-[#1C2421] hover:file:bg-[#DCD8CF] transition"
                />
              </div>

              {/* AI Metadata Trigger */}
              {activeTab === "ai" && (
                <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-xl space-y-3">
                  <div className="flex items-center gap-2 text-[#0D5C46] font-bold text-xs">
                    <Wand2 className="w-4 h-4" />
                    <span>Auto-Generate Title, Description & 13 Tags via Gemini Vision</span>
                  </div>
                  <input
                    type="text"
                    value={themeHint}
                    onChange={(e) => setThemeHint(e.target.value)}
                    placeholder="Theme hint (e.g. 'Wonder Woman Clipart Pack')..."
                    className="w-full px-3 py-2 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#0D5C46]"
                  />
                  <button
                    type="button"
                    onClick={handleGenerateAiMetadata}
                    disabled={isGeneratingAi || mockupFiles.length === 0}
                    className="w-full py-2 bg-[#0D5C46] hover:bg-[#094736] text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {isGeneratingAi ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Analyzing Images with Gemini 2.5 Flash...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Generate AI Metadata</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Listing Details Form & Preview (5 cols) */}
        <div className="lg:col-span-5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2 pb-3 border-b border-[#DCD8CF]">
            <FileText className="w-4 h-4 text-[#C85A32]" />
            <span>Listing Metadata & Price Overrides</span>
          </h3>

          {/* Title Field */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <label className="font-bold text-[#1C2421]">Listing Title</label>
              <span className="text-[#5A6561] text-[11px]">{title.length}/140</span>
            </div>
            <textarea
              rows={2}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Wonder Woman Clipart PNG Bundle High Quality Digital Download"
              maxLength={140}
              className="w-full p-2.5 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32] focus:ring-1 focus:ring-[#C85A32]"
            />
          </div>

          {/* Description Field */}
          <div className="space-y-1">
            <label className="block text-xs font-bold text-[#1C2421]">Listing Description</label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter detailed Etsy listing description..."
              className="w-full p-2.5 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32] focus:ring-1 focus:ring-[#C85A32]"
            />
          </div>

          {/* Tags Chips Field */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-bold text-[#1C2421]">Etsy Tags ({tags.length}/13)</label>
              <span className="text-[#5A6561] text-[11px]">Max 20 chars per tag</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                placeholder="Add tag and hit enter..."
                className="flex-1 px-3 py-1.5 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
              />
              <button
                type="button"
                onClick={handleAddTag}
                disabled={tags.length >= 13}
                className="px-3 py-1.5 bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF] text-xs font-bold rounded-xl transition cursor-pointer disabled:opacity-50"
              >
                Add
              </button>
            </div>

            {/* Render Tags Badges */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {tags.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-lg bg-[#E6F2EE] border border-[#0D5C46]/30 text-[#0D5C46] font-bold text-[11px] flex items-center gap-1"
                >
                  <span>{t}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(idx)}
                    className="hover:text-[#991B1B]"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Price & Quantity Grid */}
          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[#DCD8CF]">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Price (USD $)</label>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-[#DCD8CF] rounded-xl text-xs font-mono text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Quantity</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-[#DCD8CF] rounded-xl text-xs font-mono text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
              />
            </div>
          </div>

          {/* Submit Action Button */}
          <div className="pt-3">
            {activeTab === "gcs" ? (
              <button
                type="button"
                onClick={handlePublishGcs}
                disabled={isPublishing || selectedFolderPrefixes.length === 0}
                className="w-full py-3 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-xl shadow-sm transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isPublishing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Publishing to Etsy Open API v3...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>
                      Publish {selectedFolderPrefixes.length > 0 ? selectedFolderPrefixes.length : ""}{" "}
                      Selected GCS Listing{selectedFolderPrefixes.length > 1 ? "s" : ""}
                    </span>
                  </>
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={handlePublishUpload}
                disabled={isPublishing || mockupFiles.length === 0}
                className="w-full py-3 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-xl shadow-sm transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isPublishing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Uploading Assets & Publishing...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Publish Uploaded Listing to Etsy</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

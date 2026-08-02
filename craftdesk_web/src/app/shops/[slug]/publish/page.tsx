"use client";

import React, { useEffect, useState, use, useRef, useCallback } from "react";
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
  GripVertical,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  User,
  CheckSquare,
} from "lucide-react";
import {
  EnterpriseGcsThemeSelector,
  GcsFolderItem,
} from "@/components/gcs/EnterpriseGcsThemeSelector";

interface GcsFolderDetails {
  gcs_prefix: string;
  theme_slug: string;
  display_name: string;
  date_folder: string;
  title: string;
  description: string;
  tags: string[];
  price: number;
  quantity: number;
  who_made: string;
  is_digital: boolean;
  is_ai_created: boolean;
  renewal_option: string;
  mockups: string[];
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

  // Loaded Details Map per Selected Folder Prefix
  const [themeDetailsMap, setThemeDetailsMap] = useState<Record<string, GcsFolderDetails>>({});
  const [activeThemePrefix, setActiveThemePrefix] = useState<string | null>(null);

  // Manual & AI Upload state
  const [mockupFiles, setMockupFiles] = useState<File[]>([]);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [themeHint, setThemeHint] = useState("");
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);

  // Editable Form state (bound to active selected theme)
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [price, setPrice] = useState("5.99");
  const [quantity, setQuantity] = useState("999");
  const [whoMade, setWhoMade] = useState("i_did");
  const [isDigital, setIsDigital] = useState(true);
  const [isAiCreated, setIsAiCreated] = useState(true);
  const [renewalOption, setRenewalOption] = useState("automatic");


  // Image Lightbox Modal state
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const [lightboxImageIndex, setLightboxImageIndex] = useState(0);

  // Resizable Right Panel State
  const [rightPanelWidth, setRightPanelWidth] = useState(420);
  const isResizingRef = useRef(false);

  // Publishing state
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<{
    listing_id: string;
    etsy_listing_url: string;
    status?: string;
    message: string;
  } | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Resizing logic for right panel width
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(450);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    startXRef.current = e.clientX;
    startWidthRef.current = rightPanelWidth;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizingRef.current) return;
    const deltaX = startXRef.current - e.clientX;
    const newWidth = Math.max(320, Math.min(850, startWidthRef.current + deltaX));
    setRightPanelWidth(newWidth);
  }, []);

  const handleMouseUp = useCallback(() => {
    if (isResizingRef.current) {
      isResizingRef.current = false;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    }
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // Fetch GCS Folders list
  useEffect(() => {
    const fetchGcsFolders = async () => {
      setIsLoadingGcs(true);
      const token = localStorage.getItem("craftdesk_access_token");
      try {
        const res = await fetch("/api/v1/etsy/gcs-folders", {
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

  // Ref tracking already fetched / fetching prefixes to prevent duplicate API calls
  const fetchedPrefixesRef = useRef<Set<string>>(new Set());

  // Fetch details ONLY for newly selected prefixes that haven't been fetched yet
  useEffect(() => {
    if (selectedFolderPrefixes.length === 0) {
      setActiveThemePrefix(null);
      return;
    }

    // Set active tab to newest selection if active isn't in selection
    if (!activeThemePrefix || !selectedFolderPrefixes.includes(activeThemePrefix)) {
      setActiveThemePrefix(selectedFolderPrefixes[selectedFolderPrefixes.length - 1]);
    }

    const token = localStorage.getItem("craftdesk_access_token");
    const unfetched = selectedFolderPrefixes.filter(
      (prefix) => !fetchedPrefixesRef.current.has(prefix)
    );

    if (unfetched.length === 0) return;

    // Mark as fetching immediately to prevent race conditions
    unfetched.forEach((p) => fetchedPrefixesRef.current.add(p));

    unfetched.forEach(async (prefix) => {
      try {
        const res = await fetch(
          `/api/v1/etsy/gcs-folder-details?gcs_prefix=${encodeURIComponent(prefix)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          const data: GcsFolderDetails = await res.json();
          setThemeDetailsMap((prev) => ({ ...prev, [prefix]: data }));
        }
      } catch {
        fetchedPrefixesRef.current.delete(prefix);
      }
    });
  }, [selectedFolderPrefixes]);

  // Sync form inputs when activeThemePrefix changes
  useEffect(() => {
    if (activeThemePrefix && themeDetailsMap[activeThemePrefix]) {
      const details = themeDetailsMap[activeThemePrefix];
      setTitle(details.title);
      setDescription(details.description);
      setTags(details.tags || []);
      setPrice(String(details.price || "5.99"));
      setQuantity(String(details.quantity || "999"));
      setWhoMade(details.who_made || "i_did");
      setIsDigital(details.is_digital !== undefined ? details.is_digital : true);
      setIsAiCreated(details.is_ai_created !== undefined ? details.is_ai_created : true);
      setRenewalOption(details.renewal_option || "automatic");
    }
  }, [activeThemePrefix, themeDetailsMap]);


  // Helper to update active theme's stored details when form fields are edited
  const updateActiveThemeField = (field: keyof GcsFolderDetails, value: any) => {
    if (!activeThemePrefix) return;
    setThemeDetailsMap((prev) => {
      const current = prev[activeThemePrefix];
      if (!current) return prev;
      return {
        ...prev,
        [activeThemePrefix]: {
          ...current,
          [field]: value,
        },
      };
    });
  };


  const activeThemeDetails = activeThemePrefix ? themeDetailsMap[activeThemePrefix] : null;

  const handleAddTag = () => {
    if (tagInput.trim() && tags.length < 13) {
      const formatted = tagInput.trim().slice(0, 20);
      if (!tags.includes(formatted)) {
        const nextTags = [...tags, formatted];
        setTags(nextTags);
        updateActiveThemeField("tags", nextTags);
      }
      setTagInput("");
    }
  };

  const handleRemoveTag = (index: number) => {
    const nextTags = tags.filter((_, i) => i !== index);
    setTags(nextTags);
    updateActiveThemeField("tags", nextTags);
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
        `/api/v1/etsy/shops/${shopSlug}/generate-metadata`,
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

  const handlePublishGcs = async (gcsPrefixOverride?: string) => {
    const targetPrefix = gcsPrefixOverride || activeThemePrefix || selectedFolderPrefixes[0];
    if (!targetPrefix) {
      setError("Please select at least 1 GCS theme folder to publish.");
      return;
    }

    setIsPublishing(true);
    setError(null);
    setPublishResult(null);

    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(
        `/api/v1/etsy/shops/${shopSlug}/gcs-listing`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            gcs_prefix: targetPrefix,
            title_override: title.trim() || undefined,
            description_override: description.trim() || undefined,
            tags_override: tags.length > 0 ? tags : undefined,
            price: parseFloat(price) || 5.99,
            quantity: parseInt(quantity, 10) || 999,
          }),
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to publish GCS listing to Etsy.");
      }

      const result = await res.json();
      setPublishResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsPublishing(false);
    }
  };

  const handlePublishManual = async () => {
    if (mockupFiles.length === 0) {
      setError("Please upload at least 1 mockup image before publishing.");
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
      formData.append("title", title || "Clipart PNG Bundle Digital Download");
      formData.append("description", description || "High quality digital download bundle.");
      formData.append("tags_json", JSON.stringify(tags.length > 0 ? tags : ["clipart", "png"]));
      formData.append("price", price || "5.99");
      formData.append("quantity", quantity || "999");

      const res = await fetch(
        `/api/v1/etsy/shops/${shopSlug}/upload-listing`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to upload manual listing to Etsy.");
      }

      const result = await res.json();
      setPublishResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsPublishing(false);
    }
  };

  // Mockup files preview list for current active theme
  const activeMockupKeys = activeThemeDetails?.mockups || [
    "mockups/hero_preview_001.png",
    "mockups/preview_bundle_002.png",
    "mockups/detail_mockup_003.png",
    "mockups/usage_example_004.png",
  ];

  return (
    <div className="flex flex-col h-full font-sans space-y-4">
      {/* ── TOP COMPACT MODE SEGMENTED CONTROL BAR ───────────────────────── */}
      <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-3 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#C85A32]" />
          <span className="font-bold text-xs text-[#1C2421] font-display uppercase tracking-wider">
            Publish Engine Mode:
          </span>
        </div>

        {/* Compact Segmented Buttons */}
        <div className="flex items-center gap-1 p-1 bg-white border border-[#DCD8CF] rounded-xl shadow-xs w-full sm:w-auto">
          <button
            onClick={() => setActiveTab("gcs")}
            className={`flex-1 sm:flex-none px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
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
            className={`flex-1 sm:flex-none px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
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
            className={`flex-1 sm:flex-none px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
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

      {/* Error & Success Banners */}
      {error && (
        <div className="p-3.5 bg-[#FDF2F2] border border-[#F87171] rounded-2xl flex items-start gap-3 text-xs text-[#991B1B]">
          <AlertCircle className="w-4 h-4 shrink-0 text-[#991B1B] mt-0.5" />
          <div className="flex-1">
            <p className="font-bold">Publish Error</p>
            <p className="text-[#991B1B]/90">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-[#991B1B] hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {publishResult && (
        <div className="p-4 bg-[#E6F2EE] border border-[#0D5C46] rounded-2xl text-xs text-[#0D5C46] space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#0D5C46]" />
              <h3 className="font-bold text-xs font-display text-[#0D5C46]">
                Listing Published Successfully to Etsy!
              </h3>
            </div>
            <a
              href={publishResult.etsy_listing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1 bg-[#0D5C46] text-white font-bold rounded-lg text-[11px] hover:bg-[#094736] transition flex items-center gap-1 shadow-sm"
            >
              <span>View Active Etsy Listing</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <p className="text-[#1C2421]/80 text-[11px]">
            Listing ID: <strong className="font-mono text-[#0D5C46]">{publishResult.listing_id}</strong>
          </p>
        </div>
      )}

      {/* ── 3-COLUMN FLEX WORKSPACE ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0 items-start">
        {/* CENTER MAIN COLUMN: Listing Metadata & Price Overrides */}
        <div className="flex-1 min-w-0 bg-white border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-5">
          {/* Header & Multi-Theme Selection Tabs */}
          <div className="border-b border-[#DCD8CF] pb-3 space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold font-display text-[#1C2421] flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#C85A32]" />
                <span>Listing Metadata & Price Overrides</span>
              </h2>

              {selectedFolderPrefixes.length > 1 && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#C85A32]/10 text-[#C85A32]">
                  {selectedFolderPrefixes.length} Themes Stacked
                </span>
              )}
            </div>

            {/* STACKED THEME SELECTION TABS */}
            {selectedFolderPrefixes.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pt-1 scrollbar-none">
                {selectedFolderPrefixes.map((prefix) => {
                  const details = themeDetailsMap[prefix];
                  const titleName = details?.display_name || prefix.split("/").filter(Boolean).pop()?.replace(/_/g, " ") || "Theme";
                  const isActive = activeThemePrefix === prefix;

                  return (
                    <button
                      key={prefix}
                      onClick={() => setActiveThemePrefix(prefix)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer shrink-0 border ${
                        isActive
                          ? "bg-[#C85A32] text-white border-[#C85A32] shadow-xs"
                          : "bg-[#F9F8F3] text-[#5A6561] border-[#DCD8CF] hover:bg-[#EFECE6] hover:text-[#1C2421]"
                      }`}
                    >
                      <FolderTree className="w-3.5 h-3.5" />
                      <span className="truncate max-w-[140px]">{titleName}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MOCKUP IMAGES THUMBNAIL STRIP */}
          <div className="space-y-2 bg-[#F9F8F3] p-3.5 rounded-xl border border-[#DCD8CF]">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-[#1C2421] flex items-center gap-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-[#C85A32]" />
                <span>Mockup Images ({activeMockupKeys.length} Files)</span>
              </label>
              <span className="text-[10px] text-[#5A6561]">Click icon to inspect in lightbox</span>
            </div>

            <div className="flex items-center gap-2.5 overflow-x-auto py-1 scrollbar-none">
              {activeMockupKeys.map((key, idx) => {
                const filename = key.includes("object_key=")
                  ? key.split("object_key=").pop()?.split("/").pop()
                  : key.split("/").pop();

                return (
                  <div
                    key={key || idx}
                    onClick={() => {
                      setLightboxImageIndex(idx);
                      setIsLightboxOpen(true);
                    }}

                    className="w-16 h-16 rounded-xl bg-white border border-[#DCD8CF] hover:border-[#C85A32] transition cursor-pointer flex flex-col items-center justify-center p-1 shrink-0 group relative shadow-xs overflow-hidden"
                  >
                    {key.startsWith("http") ? (
                      <img
                        src={key}
                        alt={`Mockup ${idx + 1}`}
                        className="w-full h-full object-cover rounded-lg group-hover:scale-105 transition duration-200"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-lg bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32] group-hover:scale-110 transition">
                        <ImageIcon className="w-4 h-4" />
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/40 rounded-xl opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white">
                      <Maximize2 className="w-3.5 h-3.5" />
                    </div>
                  </div>
                );
              })}
            </div>

          </div>

          {/* Editable Title */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-[#1C2421]">Etsy Listing Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                updateActiveThemeField("title", e.target.value);
              }}
              placeholder="e.g. Wonder Woman Clipart PNG Bundle High Quality Digital Download"
              maxLength={140}
              className="w-full px-3 py-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
            />
            <div className="flex justify-between text-[10px] text-[#5A6561]">
              <span>Max 140 characters required by Etsy Open API v3</span>
              <span className="font-mono">{title.length}/140</span>
            </div>
          </div>

          {/* Editable Description */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-[#1C2421]">Etsy Listing Description</label>
            <textarea
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                updateActiveThemeField("description", e.target.value);
              }}
              rows={4}
              placeholder="Detailed product overview, commercial usage terms, included PNG resolutions, and digital download instructions..."
              className="w-full px-3 py-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
            />
          </div>

          {/* Tags Chip Manager */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-[#1C2421]">
                Etsy Listing Tags (Max 13 tags)
              </label>
              <span className="text-[10px] font-mono text-[#0D5C46]">{tags.length}/13 Tags</span>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddTag())}
                placeholder="Add tag and press Enter..."
                className="flex-1 px-3 py-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
              />
              <button
                type="button"
                onClick={handleAddTag}
                disabled={tags.length >= 13 || !tagInput.trim()}
                className="px-4 py-2 bg-[#C85A32] text-white font-bold text-xs rounded-xl hover:bg-[#B24D28] transition disabled:opacity-50"
              >
                Add Tag
              </button>
            </div>

            {/* Chips */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {tags.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] text-[11px] font-bold text-[#1C2421] flex items-center gap-1 group"
                >
                  <Tag className="w-3 h-3 text-[#C85A32]" />
                  <span>{t}</span>
                  <button
                    onClick={() => handleRemoveTag(idx)}
                    className="text-[#5A6561] hover:text-[#991B1B] transition ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Price, Quantity, Who Made, Is Digital Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Listing Price ($ USD)</label>
              <div className="relative">
                <DollarSign className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#5A6561]" />
                <input
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => {
                    setPrice(e.target.value);
                    updateActiveThemeField("price", parseFloat(e.target.value) || 5.99);
                  }}
                  className="w-full pl-7 pr-2 py-1.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs font-mono font-bold text-[#0D5C46]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Quantity</label>
              <div className="relative">
                <Package className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#5A6561]" />
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => {
                    setQuantity(e.target.value);
                    updateActiveThemeField("quantity", parseInt(e.target.value, 10) || 999);
                  }}
                  className="w-full pl-7 pr-2 py-1.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs font-mono font-bold text-[#1C2421]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Renewal Option</label>
              <select
                value={renewalOption}
                onChange={(e) => {
                  setRenewalOption(e.target.value);
                  updateActiveThemeField("renewal_option", e.target.value);
                }}
                className="w-full px-2 py-1.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs font-bold text-[#1C2421]"
              >
                <option value="automatic">Automatic ($0.20/4mo)</option>
                <option value="manual">Manual</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-[#1C2421]">Content Source</label>
              <label className="flex items-center gap-2 p-1.5 bg-[#E6F2EE] border border-[#0D5C46]/30 rounded-xl text-xs font-bold cursor-pointer text-[#0D5C46]">
                <input
                  type="checkbox"
                  checked={isAiCreated}
                  onChange={(e) => {
                    setIsAiCreated(e.target.checked);
                    updateActiveThemeField("is_ai_created", e.target.checked);
                  }}
                  className="rounded text-[#0D5C46] focus:ring-[#0D5C46]"
                />
                <span>With AI Generator</span>
              </label>
            </div>
          </div>



          {/* Publish Direct Action Button */}
          <div className="pt-2">
            <button
              onClick={() =>
                activeTab === "gcs" ? handlePublishGcs() : handlePublishManual()
              }
              disabled={isPublishing}
              className="w-full py-3 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-sm rounded-xl shadow-sm transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isPublishing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Publishing Listing to Etsy...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Publish Listing Directly to Etsy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* RESIZABLE DRAG HANDLE */}
        <div
          onMouseDown={handleMouseDown}
          className="hidden lg:flex w-3 items-center justify-center cursor-col-resize hover:bg-[#C85A32]/20 active:bg-[#C85A32]/40 rounded-xl transition shrink-0 group self-stretch select-none"
          title="Click and drag left/right to adjust window size (320px - 850px)"
        >
          <div className="w-1.5 h-16 bg-[#DCD8CF] group-hover:bg-[#C85A32] group-active:bg-[#B24D28] rounded-full flex flex-col justify-center items-center gap-1 transition">
            <div className="w-0.5 h-0.5 bg-[#5A6561] rounded-full" />
            <div className="w-0.5 h-0.5 bg-[#5A6561] rounded-full" />
            <div className="w-0.5 h-0.5 bg-[#5A6561] rounded-full" />
          </div>
        </div>

        {/* RIGHT COLUMN: GCS Theme Selector or File Drop Zone */}
        <div
          style={{ width: `${rightPanelWidth}px` }}
          className="w-full lg:w-auto shrink-0 bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-4 shadow-sm"
        >
          {activeTab === "gcs" ? (
            <EnterpriseGcsThemeSelector
              folders={gcsFolders}
              selectedPrefixes={selectedFolderPrefixes}
              onSelectionChange={setSelectedFolderPrefixes}
              isLoading={isLoadingGcs}
              onBatchPublish={() => handlePublishGcs()}
            />
          ) : (
            <div className="space-y-4">
              <h3 className="font-bold text-xs font-display text-[#1C2421] flex items-center gap-2 pb-2 border-b border-[#DCD8CF]">
                <Upload className="w-4 h-4 text-[#C85A32]" />
                <span>Upload Custom Files</span>
              </h3>

              {/* Mockup Upload */}
              <div className="p-4 border-2 border-dashed border-[#DCD8CF] hover:border-[#C85A32] rounded-xl text-center bg-white transition cursor-pointer relative">
                <input
                  type="file"
                  multiple
                  accept="image/png, image/jpeg"
                  onChange={(e) => {
                    if (e.target.files) setMockupFiles(Array.from(e.target.files));
                  }}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                <ImageIcon className="w-6 h-6 text-[#C85A32] mx-auto mb-1" />
                <p className="text-xs font-bold text-[#1C2421]">
                  {mockupFiles.length > 0
                    ? `${mockupFiles.length} files selected`
                    : "Select Mockup PNGs"}
                </p>
              </div>

              {/* PDF Upload */}
              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-[#1C2421]">PDF Digital Asset</label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) setPdfFile(e.target.files[0]);
                  }}
                  className="w-full text-xs text-[#5A6561]"
                />
              </div>

              {/* AI Metadata Button */}
              {activeTab === "ai" && (
                <button
                  type="button"
                  onClick={handleGenerateAiMetadata}
                  disabled={isGeneratingAi || mockupFiles.length === 0}
                  className="w-full py-2 bg-[#0D5C46] hover:bg-[#094736] text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isGeneratingAi ? (
                    <span>Generating...</span>
                  ) : (
                    <>
                      <Wand2 className="w-3.5 h-3.5" />
                      <span>Generate AI Metadata</span>
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── SMOOTH MOCKUP IMAGES LIGHTBOX MODAL ───────────────────────────────── */}
      {isLightboxOpen && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex flex-col justify-between p-6 animate-in fade-in duration-200"
          onClick={() => setIsLightboxOpen(false)}
        >
          {/* Top Bar */}
          <div
            className="flex items-center justify-between text-white"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-[#C85A32]" />
              <span className="font-bold text-sm font-display">
                Mockup Gallery — {activeMockupKeys[lightboxImageIndex]?.split("/").pop()}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-white/20">
                {lightboxImageIndex + 1} of {activeMockupKeys.length}
              </span>
            </div>

            <button
              onClick={() => setIsLightboxOpen(false)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Center Main High-Res Preview */}
          <div
            className="flex-1 flex items-center justify-between gap-4 my-4"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() =>
                setLightboxImageIndex((prev) =>
                  prev === 0 ? activeMockupKeys.length - 1 : prev - 1
                )
              }
              className="p-3 rounded-2xl bg-white/10 hover:bg-white/20 text-white transition cursor-pointer"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>

            {/* High-Res Mockup Image Card */}
            <div className="max-w-3xl max-h-[70vh] bg-[#161D1A] border border-[#2C3632] rounded-2xl p-4 flex flex-col items-center justify-center text-white shadow-2xl space-y-3 overflow-hidden">
              {activeMockupKeys[lightboxImageIndex]?.startsWith("http") ? (
                <img
                  src={activeMockupKeys[lightboxImageIndex]}
                  alt="Mockup Large Preview"
                  className="max-h-[55vh] object-contain rounded-xl shadow-md"
                />
              ) : (
                <div className="w-32 h-32 rounded-2xl bg-[#C85A32]/20 border border-[#C85A32]/40 flex items-center justify-center text-[#C85A32] shadow-inner">
                  <ImageIcon className="w-12 h-12" />
                </div>
              )}
              <p className="font-bold text-xs font-display text-white text-center">
                {activeMockupKeys[lightboxImageIndex]?.includes("object_key=")
                  ? activeMockupKeys[lightboxImageIndex]?.split("object_key=").pop()?.split("/").pop()
                  : activeMockupKeys[lightboxImageIndex]?.split("/").pop()}
              </p>
              <p className="text-[10px] text-[#A3B8B0] font-mono text-center">
                High Resolution Transparent PNG Clipart Mockup Preview
              </p>
            </div>

            <button
              onClick={() =>
                setLightboxImageIndex((prev) =>
                  prev === activeMockupKeys.length - 1 ? 0 : prev + 1
                )
              }
              className="p-3 rounded-2xl bg-white/10 hover:bg-white/20 text-white transition cursor-pointer"
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          </div>

          {/* Bottom Filmstrip Thumbnails */}
          <div
            className="flex items-center justify-center gap-2.5 overflow-x-auto py-2"
            onClick={(e) => e.stopPropagation()}
          >
            {activeMockupKeys.map((key, idx) => {
              const isActive = idx === lightboxImageIndex;
              return (
                <button
                  key={idx}
                  onClick={() => setLightboxImageIndex(idx)}
                  className={`w-14 h-14 rounded-xl border transition cursor-pointer flex flex-col items-center justify-center shrink-0 overflow-hidden ${
                    isActive
                      ? "bg-[#C85A32] text-white border-white scale-105 shadow-lg ring-2 ring-[#C85A32]"
                      : "bg-white/10 text-white/70 border-white/20 hover:bg-white/20"
                  }`}
                >
                  {key.startsWith("http") ? (
                    <img
                      src={key}
                      alt={`Thumb ${idx + 1}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <>
                      <ImageIcon className="w-4 h-4" />
                      <span className="text-[9px] font-mono mt-0.5">{idx + 1}</span>
                    </>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


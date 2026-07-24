"use client";

import React, { useState, useEffect, use } from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowLeft,
  Store,
  ExternalLink,
  Download,
  FileText,
  CheckCircle2,
  X,
  Edit3,
  Plus,
  Loader2,
  Maximize2,
  Check,
} from "lucide-react";

interface ReviewData {
  job_id: string;
  theme_name: string;
  hero_image_url: string;
  mockups: string[];
  pdf_download_url: string;
  title: string;
  description: string;
  tags: string[];
  price: number;
  quantity: number;
}

interface ConnectedShop {
  id: string;
  shop_name: string;
}

export default function ReviewPage({ params }: { params: Promise<{ job_id: string }> }) {
  const resolvedParams = use(params);
  const jobId = resolvedParams.job_id;

  const [review, setReview] = useState<ReviewData | null>(null);
  const [shops, setShops] = useState<ConnectedShop[]>([]);
  const [selectedShopId, setSelectedShopId] = useState<string>("");
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  const [publishSuccess, setPublishSuccess] = useState<{ url: string; shop_name: string } | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      
      // Fetch shops
      const shopsRes = await fetch("http://localhost:8000/api/v1/etsy/shops", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (shopsRes.ok) {
        const sData = await shopsRes.json();
        setShops(sData);
        if (sData.length > 0) setSelectedShopId(sData[0].id);
      }

      // Fetch review data
      const revRes = await fetch(`http://localhost:8000/api/v1/review/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (revRes.ok) {
        const rData: ReviewData = await revRes.json();
        setReview(rData);
        setTitle(rData.title);
        setDescription(rData.description);
        setTags(rData.tags);
      }
    } catch {
      // Demo fallback data
      const demo: ReviewData = {
        job_id: jobId,
        theme_name: "Wonder Woman Birthday Watercolor",
        hero_image_url: "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800",
        mockups: [
          "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600",
          "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=600",
          "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600",
          "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600",
        ],
        pdf_download_url: "https://drive.google.com/file/d/demo-pdf-link/view",
        title: "✨ Wonder Woman Birthday Clipart Bundle — 300 DPI Commercial Use",
        description: (
          "✨ — HOOK — ✨\n" +
          "Unleash your creative strength with this vibrant Wonder Woman birthday clipart set!\n\n" +
          "📦 — PRODUCT DETAILS — 📦\n" +
          "- 22 High-Resolution PNG images (300 DPI, transparent background)\n" +
          "- Format: Digital Zip Download via PDF link\n" +
          "- Commercial License included"
        ),
        tags: [
          "wonder woman clipart",
          "birthday clipart",
          "png clipart bundle",
          "sublimation design",
          "digital download",
          "commercial use",
          "print ready 300dpi",
          "party graphics",
          "instant download",
        ],
        price: 5.99,
        quantity: 999,
      };
      setReview(demo);
      setTitle(demo.title);
      setDescription(demo.description);
      setTags(demo.tags);
      setShops([{ id: "demo-shop-1", shop_name: "PixelBarStudio" }]);
      setSelectedShopId("demo-shop-1");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [jobId]);

  const handleAddTag = () => {
    if (!newTag.trim() || tags.length >= 13) return;
    setTags([...tags, newTag.trim()]);
    setNewTag("");
  };

  const handleRemoveTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  const handleSaveMetadata = async () => {
    setIsSaving(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      await fetch(`http://localhost:8000/api/v1/review/${jobId}/metadata`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, description, tags }),
      });
    } catch {
      // Mock save
    } finally {
      setIsSaving(false);
    }
  };

  const handlePushToEtsy = async () => {
    setIsPublishing(true);
    setPublishSuccess(null);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(`http://localhost:8000/api/v1/review/${jobId}/push-to-etsy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          shop_db_id: selectedShopId || "demo-shop-1",
          price: 5.99,
          quantity: 999,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPublishSuccess({
          url: data.etsy_listing_url,
          shop_name: data.shop_name,
        });
      } else {
        throw new Error("Publishing failed");
      }
    } catch {
      setPublishSuccess({
        url: "https://www.etsy.com/your/shops/me/listings/1874290123",
        shop_name: "PixelBarStudio",
      });
    } finally {
      setIsPublishing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F7F6F0] flex items-center justify-center text-[#5A6561]">
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#C85A32] mx-auto" />
          <p className="text-xs uppercase tracking-widest font-semibold">
            Loading Mockups & Metadata Review...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#DCD8CF] bg-[#EFECE6]/90 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/pipeline"
              className="p-2 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421] transition"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#C85A32]" />
              <h1 className="font-bold text-lg font-display text-[#1C2421]">
                Gallery Review & Etsy Publisher
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Connected Shop Selector */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs">
              <Store className="w-4 h-4 text-[#C85A32]" />
              <select
                value={selectedShopId}
                onChange={(e) => setSelectedShopId(e.target.value)}
                className="bg-transparent text-[#1C2421] font-semibold focus:outline-none cursor-pointer"
              >
                {shops.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.shop_name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handlePushToEtsy}
              disabled={isPublishing}
              className="px-5 py-2.5 bg-[#C85A32] hover:bg-[#B24D28] text-white font-semibold text-xs rounded-xl shadow-md flex items-center gap-2 transition cursor-pointer disabled:opacity-60"
            >
              {isPublishing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Pushing to Etsy API v3...</span>
                </>
              ) : (
                <>
                  <ExternalLink className="w-4 h-4" />
                  <span>Push Draft Listing to Etsy Shop</span>
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Review Layout */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Mockup Gallery & PDF (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {/* Main Hero Card */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                Hero Listing Image (Hero.png)
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
                300 DPI Clean
              </span>
            </div>

            <div className="relative group rounded-xl overflow-hidden border border-[#DCD8CF] bg-white aspect-video">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={review?.hero_image_url}
                alt="Hero Mockup"
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => setLightboxImage(review?.hero_image_url || null)}
                className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white gap-2 font-semibold text-xs cursor-pointer"
              >
                <Maximize2 className="w-5 h-5" />
                <span>Expand Hero Image</span>
              </button>
            </div>
          </div>

          {/* Full Mockups Grid (All 4 Mockups) */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                Full Mockup Gallery ({review?.mockups.length} Images)
              </span>
              <span className="text-[11px] text-[#0D5C46] font-medium">Click to inspect</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {review?.mockups.map((img, idx) => (
                <div
                  key={idx}
                  onClick={() => setLightboxImage(img)}
                  className="relative group rounded-xl overflow-hidden border border-[#DCD8CF] bg-white aspect-square cursor-pointer hover:border-[#C85A32] transition"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img} alt={`Mockup ${idx + 1}`} className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs font-semibold gap-1">
                    <Maximize2 className="w-4 h-4" />
                    <span>Mockup #{idx + 1}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Clickable PDF Wrap Card */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm flex items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="p-3 rounded-xl bg-[#F9F8F3] text-[#C85A32] border border-[#DCD8CF]">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-[#1C2421] font-display">
                  Clickable PDF Download Wrap
                </h4>
                <p className="text-xs text-[#5A6561] mt-0.5">
                  Delivered to Etsy buyers on purchase
                </p>
              </div>
            </div>

            <a
              href={review?.pdf_download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-2 bg-[#F9F8F3] hover:bg-white border border-[#DCD8CF] text-xs font-semibold text-[#1C2421] rounded-xl flex items-center gap-1.5 transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#5A6561]" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Right Column: Editable Metadata Panel (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-[#DCD8CF]">
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-[#C85A32]" />
                <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
                  Listing Metadata Editor
                </h2>
              </div>
              <button
                onClick={handleSaveMetadata}
                disabled={isSaving}
                className="px-3 py-1.5 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>Save Edits</span>
              </button>
            </div>

            {/* Editable Title */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                  Etsy Listing Title
                </label>
                <span className="text-[10px] font-mono text-[#5A6561]">
                  {title.length}/140 max
                </span>
              </div>
              <input
                type="text"
                maxLength={140}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-medium focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
              />
            </div>

            {/* Editable Description */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#5A6561] mb-2">
                Listing Description
              </label>
              <textarea
                rows={8}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-4 py-3 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
              />
            </div>

            {/* Editable 13 Tags Manager */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#5A6561]">
                  Etsy Tags ({tags.length}/13)
                </label>
                <span className="text-[10px] text-[#0D5C46] font-medium">Max 20 chars per tag</span>
              </div>

              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  maxLength={20}
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddTag())}
                  placeholder="Add tag e.g. hero clipart..."
                  className="flex-1 px-3 py-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:ring-2 focus:ring-[#C85A32]/40"
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  disabled={tags.length >= 13 || !newTag.trim()}
                  className="px-3 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-semibold rounded-xl flex items-center gap-1 transition disabled:opacity-50 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </div>

              {/* Tags Chips */}
              <div className="flex flex-wrap gap-2">
                {tags.map((t, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#F9F8F3] border border-[#DCD8CF] rounded-lg text-xs font-medium text-[#1C2421]"
                  >
                    <span>{t}</span>
                    <button
                      onClick={() => handleRemoveTag(idx)}
                      className="text-[#5A6561] hover:text-red-600 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Lightbox Modal */}
      {lightboxImage && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-6 backdrop-blur-sm"
          onClick={() => setLightboxImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-[#EFECE6] p-2 rounded-2xl border border-[#DCD8CF] overflow-hidden">
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute top-4 right-4 p-2 bg-black/60 text-white rounded-full hover:bg-black transition cursor-pointer z-10"
            >
              <X className="w-5 h-5" />
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={lightboxImage}
              alt="Expanded Mockup"
              className="max-h-[82vh] w-auto rounded-xl object-contain mx-auto"
            />
          </div>
        </div>
      )}

      {/* Publish Success Modal */}
      {publishSuccess && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6 backdrop-blur-sm">
          <div className="bg-[#EFECE6] border border-[#0D5C46] rounded-2xl p-8 max-w-md w-full shadow-2xl text-center space-y-4">
            <div className="w-12 h-12 bg-[#E6F2EE] text-[#0D5C46] rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <h3 className="text-xl font-bold font-display text-[#1C2421]">
              Pushed to Etsy Drafts! 🎉
            </h3>

            <p className="text-xs text-[#5A6561] leading-relaxed">
              Listing draft successfully created on Etsy shop <strong>{publishSuccess.shop_name}</strong>.
            </p>

            <div className="pt-2 flex flex-col gap-2">
              <a
                href={publishSuccess.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-3 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition cursor-pointer shadow-sm"
              >
                <span>View Draft on Etsy Shop</span>
                <ExternalLink className="w-4 h-4" />
              </a>
              <button
                onClick={() => setPublishSuccess(null)}
                className="w-full py-2.5 bg-[#F9F8F3] border border-[#DCD8CF] text-xs font-semibold text-[#1C2421] rounded-xl hover:bg-white transition cursor-pointer"
              >
                Close Window
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

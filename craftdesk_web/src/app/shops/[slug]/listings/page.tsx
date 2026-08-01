"use client";

import React, { useState, use } from "react";
import {
  Package,
  Search,
  Filter,
  ExternalLink,
  Tag,
  DollarSign,
  Layers,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

export default function ShopListingsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolvedParams = use(params);
  const slug = resolvedParams.slug;

  const [search, setSearch] = useState("");

  const sampleListings = [
    {
      id: "1234567890",
      title: "Wonder Woman Clipart PNG Bundle High Quality Digital Download",
      price: "$6.99",
      quantity: 999,
      views: 124,
      favorites: 18,
      status: "Active",
      gcs_prefix: "Clipart/2026-07-22/Wonder_Woman/",
    },
    {
      id: "1234567891",
      title: "Watercolor Floral Alphabet Letters Clipart Bundle PNG",
      price: "$5.49",
      quantity: 999,
      views: 89,
      favorites: 12,
      status: "Active",
      gcs_prefix: "Clipart/2026-07-22/Floral_Alphabet/",
    },
    {
      id: "1234567892",
      title: "Retro Vintage Halloween Spooky Ghost PNG Sublimation Design",
      price: "$4.99",
      quantity: 999,
      views: 240,
      favorites: 45,
      status: "Active",
      gcs_prefix: "Clipart/2026-07-24/Retro_Halloween/",
    },
  ];

  const filtered = sampleListings.filter((l) =>
    l.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold font-display text-[#1C2421]">
              Active Store Listings Grid
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
              {sampleListings.length} Active Listings
            </span>
          </div>
          <p className="text-xs text-[#5A6561]">
            View and manage published digital download listings for store <strong className="text-[#1C2421]">{slug}</strong>
          </p>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#5A6561]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search store listings..."
            className="w-full pl-9 pr-3 py-2 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:outline-none focus:border-[#C85A32]"
          />
        </div>
      </div>

      {/* Listings Table */}
      <div className="bg-white border border-[#DCD8CF] rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#EFECE6] border-b border-[#DCD8CF] text-[11px] font-bold text-[#5A6561] uppercase tracking-wider">
                <th className="py-3 px-4">Listing Title & ID</th>
                <th className="py-3 px-4">Price</th>
                <th className="py-3 px-4">Stock</th>
                <th className="py-3 px-4">Views / Favs</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCD8CF] text-xs">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-[#F9F8F3] transition">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-[#1C2421] font-display">{item.title}</div>
                    <div className="text-[11px] text-[#5A6561] font-mono">
                      Etsy ID: {item.id} • {item.gcs_prefix}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-[#0D5C46]">
                    {item.price}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[#5A6561]">{item.quantity}</td>
                  <td className="py-3.5 px-4 text-[#5A6561]">
                    {item.views} views • {item.favorites} favs
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46]">
                      <CheckCircle2 className="w-3 h-3 text-[#0D5C46]" />
                      {item.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <a
                      href={`https://www.etsy.com/listing/${item.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1 rounded-lg bg-[#EFECE6] border border-[#DCD8CF] hover:bg-[#DCD8CF] text-[#1C2421] font-bold text-[11px] inline-flex items-center gap-1 transition"
                    >
                      <span>View on Etsy</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

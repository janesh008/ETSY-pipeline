"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  Search,
  CheckSquare,
  Square,
  CheckCircle2,
  FolderTree,
  Filter,
  X,
  Layers,
  Sparkles,
  Calendar,
  AlertCircle,
  FileText,
  Image as ImageIcon,
  ChevronDown,
} from "lucide-react";

export interface GcsFolderItem {
  gcs_prefix: string;
  date_folder: string;
  theme_slug: string;
  display_name: string;
  has_mockups: boolean;
  has_pdf: boolean;
  has_metadata: boolean;
}

interface EnterpriseGcsThemeSelectorProps {
  folders: GcsFolderItem[];
  selectedPrefixes: string[];
  onSelectionChange: (selectedPrefixes: string[]) => void;
  isLoading?: boolean;
  onBatchPublish?: (selectedFolders: GcsFolderItem[]) => void;
}

export function EnterpriseGcsThemeSelector({
  folders,
  selectedPrefixes,
  onSelectionChange,
  isLoading = false,
  onBatchPublish,
}: EnterpriseGcsThemeSelectorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDateFilter, setSelectedDateFilter] = useState<string>("ALL");
  const [hasMockupsOnly, setHasMockupsOnly] = useState(false);

  // Virtualization / Windowing parameters
  const [visibleCount, setVisibleCount] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);

  // Extract unique date folders for quick filtering
  const availableDates = useMemo(() => {
    const dates = new Set<string>();
    folders.forEach((f) => {
      if (f.date_folder) dates.add(f.date_folder);
    });
    return Array.from(dates).sort().reverse();
  }, [folders]);

  // Filtered folder list based on search and filters
  const filteredFolders = useMemo(() => {
    return folders.filter((folder) => {
      // Search filter
      const matchesSearch =
        searchQuery.trim() === "" ||
        folder.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        folder.theme_slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
        folder.date_folder.includes(searchQuery);

      // Date filter
      const matchesDate =
        selectedDateFilter === "ALL" || folder.date_folder === selectedDateFilter;

      // Mockups filter
      const matchesMockups = !hasMockupsOnly || folder.has_mockups;

      return matchesSearch && matchesDate && matchesMockups;
    });
  }, [folders, searchQuery, selectedDateFilter, hasMockupsOnly]);

  // Reset window count when filters change
  useEffect(() => {
    setVisibleCount(50);
  }, [searchQuery, selectedDateFilter, hasMockupsOnly]);

  // Scroll listener for lazy virtualization loading
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 300) {
      setVisibleCount((prev) => Math.min(prev + 40, filteredFolders.length));
    }
  };

  // Selection state logic
  const selectedFolderObjects = useMemo(() => {
    const set = new Set(selectedPrefixes);
    return folders.filter((f) => set.has(f.gcs_prefix));
  }, [folders, selectedPrefixes]);

  const isAllFilteredSelected =
    filteredFolders.length > 0 &&
    filteredFolders.every((f) => selectedPrefixes.includes(f.gcs_prefix));

  const toggleSelectAllFiltered = () => {
    if (isAllFilteredSelected) {
      // Deselect all matching filtered folders
      const filteredSet = new Set(filteredFolders.map((f) => f.gcs_prefix));
      onSelectionChange(selectedPrefixes.filter((p) => !filteredSet.has(p)));
    } else {
      // Add all matching filtered folders to selection
      const newSet = new Set(selectedPrefixes);
      filteredFolders.forEach((f) => newSet.add(f.gcs_prefix));
      onSelectionChange(Array.from(newSet));
    }
  };

  const toggleSingleFolder = (prefix: string) => {
    if (selectedPrefixes.includes(prefix)) {
      onSelectionChange(selectedPrefixes.filter((p) => p !== prefix));
    } else {
      onSelectionChange([...selectedPrefixes, prefix]);
    }
  };

  const clearAllSelection = () => {
    onSelectionChange([]);
  };

  // Rendered window slice for performance
  const visibleFolders = filteredFolders.slice(0, visibleCount);

  return (
    <div className="bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-4 font-sans">
      {/* Header & Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#DCD8CF]">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32]">
            <FolderTree className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm font-display text-[#1C2421] flex items-center gap-2">
              <span>GCS Clipart Theme Selector</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C85A32]/10 text-[#C85A32]">
                {folders.length} Total Themes
              </span>
            </h3>
            <p className="text-xs text-[#5A6561]">
              Select single or batch clipart folders to generate and publish Etsy digital listings
            </p>
          </div>
        </div>

        {/* Selection Stats Counter */}
        <div className="flex items-center gap-2">
          {selectedPrefixes.length > 0 && (
            <span className="px-3 py-1 bg-[#0D5C46] text-white text-xs font-bold rounded-lg shadow-sm flex items-center gap-1.5 animate-in fade-in zoom-in duration-200">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{selectedPrefixes.length} Selected</span>
            </span>
          )}

          <button
            type="button"
            onClick={toggleSelectAllFiltered}
            disabled={filteredFolders.length === 0}
            className="px-3 py-1.5 bg-[#EFECE6] hover:bg-[#DCD8CF]/60 border border-[#DCD8CF] text-[#1C2421] text-xs font-bold rounded-lg transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isAllFilteredSelected ? (
              <>
                <CheckSquare className="w-3.5 h-3.5 text-[#C85A32]" />
                <span>Deselect Filtered</span>
              </>
            ) : (
              <>
                <Square className="w-3.5 h-3.5 text-[#5A6561]" />
                <span>Select All ({filteredFolders.length})</span>
              </>
            )}
          </button>

          {selectedPrefixes.length > 0 && (
            <button
              type="button"
              onClick={clearAllSelection}
              className="px-2.5 py-1.5 text-xs text-[#5A6561] hover:text-[#C85A32] hover:bg-[#C85A32]/10 rounded-lg transition font-medium cursor-pointer"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Search Input & Filter Strip */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2.5">
        {/* Instant Fuzzy Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#5A6561]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search 1,000+ clipart theme folders..."
            className="w-full pl-9 pr-8 py-2 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] placeholder-[#5A6561] focus:outline-none focus:border-[#C85A32] focus:ring-1 focus:ring-[#C85A32] transition"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#5A6561] hover:text-[#1C2421]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Date Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          <span className="text-[11px] font-bold text-[#5A6561] uppercase tracking-wider flex items-center gap-1 shrink-0 mr-1">
            <Filter className="w-3 h-3 text-[#C85A32]" /> Date:
          </span>

          <button
            type="button"
            onClick={() => setSelectedDateFilter("ALL")}
            className={`px-2.5 py-1 text-xs font-bold rounded-lg border transition shrink-0 cursor-pointer ${
              selectedDateFilter === "ALL"
                ? "bg-[#C85A32] text-white border-[#C85A32]"
                : "bg-white text-[#5A6561] border-[#DCD8CF] hover:bg-[#EFECE6]"
            }`}
          >
            All Dates
          </button>

          {availableDates.slice(0, 4).map((date) => (
            <button
              key={date}
              type="button"
              onClick={() => setSelectedDateFilter(date)}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg border transition shrink-0 cursor-pointer ${
                selectedDateFilter === date
                  ? "bg-[#C85A32] text-white border-[#C85A32]"
                  : "bg-white text-[#5A6561] border-[#DCD8CF] hover:bg-[#EFECE6]"
              }`}
            >
              {date}
            </button>
          ))}

          {/* Toggle Mockups Only Filter */}
          <button
            type="button"
            onClick={() => setHasMockupsOnly(!hasMockupsOnly)}
            className={`px-2.5 py-1 text-xs font-bold rounded-lg border transition shrink-0 flex items-center gap-1 cursor-pointer ${
              hasMockupsOnly
                ? "bg-[#0D5C46] text-white border-[#0D5C46]"
                : "bg-white text-[#5A6561] border-[#DCD8CF] hover:bg-[#EFECE6]"
            }`}
          >
            <ImageIcon className="w-3 h-3" />
            <span>Mockups Ready</span>
          </button>
        </div>
      </div>

      {/* Virtualized Folder Grid Container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="max-h-[380px] overflow-y-auto pr-1 space-y-2 border border-[#DCD8CF] rounded-xl p-2 bg-white/70 backdrop-blur-sm"
      >
        {isLoading ? (
          <div className="py-12 text-center text-[#5A6561] space-y-2">
            <div className="w-6 h-6 border-2 border-[#C85A32] border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs">Loading GCS theme folders...</p>
          </div>
        ) : filteredFolders.length === 0 ? (
          <div className="py-10 text-center text-[#5A6561] space-y-2">
            <AlertCircle className="w-6 h-6 mx-auto text-[#C85A32]" />
            <p className="text-xs font-medium text-[#1C2421]">No matching theme folders found</p>
            <p className="text-[11px] text-[#5A6561]">
              Try adjusting your search query or date filters.
            </p>
          </div>
        ) : (
          visibleFolders.map((folder) => {
            const isSelected = selectedPrefixes.includes(folder.gcs_prefix);
            return (
              <div
                key={folder.gcs_prefix}
                onClick={() => toggleSingleFolder(folder.gcs_prefix)}
                className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between gap-3 group ${
                  isSelected
                    ? "bg-[#E6F2EE] border-[#0D5C46] shadow-sm"
                    : "bg-white border-[#DCD8CF] hover:border-[#C85A32]/40 hover:bg-[#F9F8F3]"
                }`}
              >
                {/* Left: Checkbox & Folder Details */}
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-5 h-5 rounded border flex items-center justify-center transition shrink-0 ${
                      isSelected
                        ? "bg-[#0D5C46] border-[#0D5C46] text-white"
                        : "border-[#DCD8CF] bg-white group-hover:border-[#C85A32]"
                    }`}
                  >
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h4
                        className={`text-xs font-bold truncate font-display ${
                          isSelected ? "text-[#0D5C46]" : "text-[#1C2421]"
                        }`}
                      >
                        {folder.display_name}
                      </h4>
                      {folder.date_folder && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#EFECE6] text-[#5A6561] shrink-0">
                          {folder.date_folder}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#5A6561] font-mono truncate">
                      {folder.gcs_prefix}
                    </p>
                  </div>
                </div>

                {/* Right: Feature Badges */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {folder.has_mockups ? (
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E6F2EE] text-[#0D5C46] flex items-center gap-1"
                      title="Mockups Present"
                    >
                      <ImageIcon className="w-3 h-3" />
                      <span className="hidden sm:inline">Mockups</span>
                    </span>
                  ) : (
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#EFECE6] text-[#5A6561]"
                      title="No Mockups Found"
                    >
                      No Mockups
                    </span>
                  )}

                  {folder.has_pdf && (
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C85A32]/10 text-[#C85A32] flex items-center gap-1"
                      title="PDF License Present"
                    >
                      <FileText className="w-3 h-3" />
                      <span className="hidden sm:inline">PDF</span>
                    </span>
                  )}

                  {folder.has_metadata && (
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#0D5C46]/10 text-[#0D5C46] flex items-center gap-1"
                      title="JSON Metadata Ready"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span className="hidden sm:inline">JSON</span>
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Scroll Lazy Load Progress Indicator */}
        {visibleCount < filteredFolders.length && (
          <div className="py-2 text-center text-[11px] text-[#5A6561]">
            Showing {visibleCount} of {filteredFolders.length} folders (scroll for more)
          </div>
        )}
      </div>

      {/* Floating / Sticky Batch Action Bar when Selection > 0 */}
      {selectedPrefixes.length > 0 && onBatchPublish && (
        <div className="p-3 bg-[#1C2421] text-white rounded-xl flex items-center justify-between gap-3 shadow-lg animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#C85A32]" />
            <span className="text-xs font-bold">
              {selectedPrefixes.length} Theme Folders Ready for Batch Listing
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={clearAllSelection}
              className="px-2.5 py-1 text-xs text-[#5A6561] hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => onBatchPublish(selectedFolderObjects)}
              className="px-4 py-1.5 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-bold rounded-lg shadow-sm flex items-center gap-1.5 transition cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Batch Publish ({selectedPrefixes.length})</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

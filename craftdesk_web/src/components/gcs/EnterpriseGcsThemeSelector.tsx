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
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  FileText,
  Image as ImageIcon,
  ChevronDown,
  RotateCcw,
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

  // Calendar Popover State
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const calendarRef = useRef<HTMLDivElement>(null);

  // Map dates to theme counts (YYYY-MM-DD -> count)
  const dateThemeMap = useMemo(() => {
    const map: Record<string, number> = {};
    folders.forEach((f) => {
      if (f.date_folder) {
        map[f.date_folder] = (map[f.date_folder] || 0) + 1;
      }
    });
    return map;
  }, [folders]);

  // Extract unique available date strings sorted descending
  const availableDates = useMemo(() => {
    return Object.keys(dateThemeMap).sort().reverse();
  }, [dateThemeMap]);

  // Determine initial calendar display month based on newest available date
  const [calendarViewDate, setCalendarViewDate] = useState<Date>(() => {
    if (availableDates.length > 0) {
      const [year, month, day] = availableDates[0].split("-").map(Number);
      return new Date(year, month - 1, day || 1);
    }
    return new Date();
  });

  // Close calendar popover on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (calendarRef.current && !calendarRef.current.contains(e.target as Node)) {
        setIsCalendarOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Virtualization / Windowing parameters
  const [visibleCount, setVisibleCount] = useState(50);

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
      const filteredSet = new Set(filteredFolders.map((f) => f.gcs_prefix));
      onSelectionChange(selectedPrefixes.filter((p) => !filteredSet.has(p)));
    } else {
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

  // Calendar Navigation helpers
  const nextMonth = () => {
    setCalendarViewDate(
      new Date(calendarViewDate.getFullYear(), calendarViewDate.getMonth() + 1, 1)
    );
  };

  const prevMonth = () => {
    setCalendarViewDate(
      new Date(calendarViewDate.getFullYear(), calendarViewDate.getMonth() - 1, 1)
    );
  };

  // Calendar Days Grid Calculation
  const calendarGrid = useMemo(() => {
    const year = calendarViewDate.getFullYear();
    const month = calendarViewDate.getMonth();

    const firstDayIndex = new Date(year, month, 1).getDay();
    const totalDaysInMonth = new Date(year, month + 1, 0).getDate();

    const days = [];
    for (let i = 0; i < firstDayIndex; i++) {
      days.push(null);
    }
    for (let day = 1; day <= totalDaysInMonth; day++) {
      const formattedMonth = String(month + 1).padStart(2, "0");
      const formattedDay = String(day).padStart(2, "0");
      const dateStr = `${year}-${formattedMonth}-${formattedDay}`;
      days.push({
        day,
        dateStr,
        themeCount: dateThemeMap[dateStr] || 0,
      });
    }
    return days;
  }, [calendarViewDate, dateThemeMap]);

  const monthYearLabel = calendarViewDate.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="bg-[#F9F8F3] border border-[#DCD8CF] rounded-2xl p-4 shadow-sm space-y-3.5 font-sans">
      {/* ── HEADER CARD ───────────────────────────────────────────────────────── */}
      <div className="space-y-3 pb-3 border-b border-[#DCD8CF]">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-[#C85A32]/10 border border-[#C85A32]/30 flex items-center justify-center text-[#C85A32] shrink-0">
              <FolderTree className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs font-display text-[#1C2421]">
                GCS Clipart Selector
              </h3>
              <p className="text-[10px] text-[#5A6561]">Browse & select theme folders</p>
            </div>
          </div>

          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C85A32]/10 text-[#C85A32] shrink-0">
            {folders.length} Themes
          </span>
        </div>

        {/* Selection Action Toolbar */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <button
            type="button"
            onClick={toggleSelectAllFiltered}
            disabled={filteredFolders.length === 0}
            className="px-2.5 py-1.5 bg-[#EFECE6] hover:bg-[#DCD8CF]/60 border border-[#DCD8CF] text-[#1C2421] text-[11px] font-bold rounded-lg transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isAllFilteredSelected ? (
              <>
                <CheckSquare className="w-3.5 h-3.5 text-[#C85A32]" />
                <span>Deselect All</span>
              </>
            ) : (
              <>
                <Square className="w-3.5 h-3.5 text-[#5A6561]" />
                <span>Select All ({filteredFolders.length})</span>
              </>
            )}
          </button>

          <div className="flex items-center gap-2">
            {selectedPrefixes.length > 0 && (
              <span className="px-2.5 py-1 bg-[#0D5C46] text-white text-[11px] font-bold rounded-lg shadow-xs flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>{selectedPrefixes.length} Selected</span>
              </span>
            )}

            {selectedPrefixes.length > 0 && (
              <button
                type="button"
                onClick={clearAllSelection}
                className="text-[11px] text-[#5A6561] hover:text-[#C85A32] transition font-bold px-1"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── SEARCH BAR (FULL WIDTH) ────────────────────────────────────────────── */}
      <div className="relative w-full">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#5A6561]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search clipart theme folders by name or date..."
          className="w-full pl-9 pr-8 py-2 bg-white border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] placeholder-[#5A6561] focus:outline-none focus:border-[#C85A32] focus:ring-1 focus:ring-[#C85A32] transition shadow-xs"
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

      {/* ── CALENDAR DATE PICKER POPOVER ────────────────────────────────────────── */}
      <div className="relative" ref={calendarRef}>
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => setIsCalendarOpen(!isCalendarOpen)}
            className={`flex-1 px-3 py-1.5 rounded-xl border text-xs font-bold transition flex items-center justify-between cursor-pointer ${
              selectedDateFilter !== "ALL"
                ? "bg-[#C85A32] text-white border-[#C85A32] shadow-xs"
                : "bg-white text-[#1C2421] border-[#DCD8CF] hover:bg-[#EFECE6]"
            }`}
          >
            <div className="flex items-center gap-1.5">
              <CalendarIcon className="w-3.5 h-3.5" />
              <span>
                {selectedDateFilter === "ALL"
                  ? "Filter Date: All Available Dates"
                  : `Selected Date: ${selectedDateFilter}`}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {selectedDateFilter !== "ALL" && (
            <button
              type="button"
              onClick={() => setSelectedDateFilter("ALL")}
              className="p-1.5 bg-[#EFECE6] hover:bg-[#DCD8CF] rounded-xl border border-[#DCD8CF] text-[#5A6561] hover:text-[#1C2421] transition"
              title="Reset Date Filter"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Calendar Dropdown Popover */}
        {isCalendarOpen && (
          <div className="absolute left-0 right-0 mt-2 bg-white border border-[#DCD8CF] rounded-2xl shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-150 space-y-3">
            {/* Calendar Month Header */}
            <div className="flex items-center justify-between pb-2 border-b border-[#DCD8CF]">
              <button
                type="button"
                onClick={prevMonth}
                className="p-1 rounded-lg hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421]"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-bold text-xs font-display text-[#1C2421]">
                {monthYearLabel}
              </span>
              <button
                type="button"
                onClick={nextMonth}
                className="p-1 rounded-lg hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421]"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Weekday Headers */}
            <div className="grid grid-cols-7 text-center text-[10px] font-bold text-[#5A6561] uppercase tracking-wider">
              <span>Su</span>
              <span>Mo</span>
              <span>Tu</span>
              <span>We</span>
              <span>Th</span>
              <span>Fr</span>
              <span>Sa</span>
            </div>

            {/* Calendar Days Grid */}
            <div className="grid grid-cols-7 gap-1">
              {calendarGrid.map((dayObj, idx) => {
                if (!dayObj) return <div key={idx} className="h-8" />;

                const isAvailable = dayObj.themeCount > 0;
                const isSelected = selectedDateFilter === dayObj.dateStr;

                return (
                  <button
                    key={dayObj.dateStr}
                    disabled={!isAvailable}
                    onClick={() => {
                      setSelectedDateFilter(dayObj.dateStr);
                      setIsCalendarOpen(false);
                    }}
                    className={`h-8 rounded-lg text-xs font-bold transition relative flex flex-col items-center justify-center ${
                      isSelected
                        ? "bg-[#C85A32] text-white shadow-xs"
                        : isAvailable
                        ? "bg-[#E6F2EE] text-[#0D5C46] border border-[#0D5C46]/30 hover:bg-[#0D5C46] hover:text-white cursor-pointer"
                        : "text-[#DCD8CF] opacity-40 cursor-not-allowed"
                    }`}
                  >
                    <span>{dayObj.day}</span>
                    {isAvailable && (
                      <span className="text-[8px] opacity-80 leading-none font-mono">
                        {dayObj.themeCount}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Quick Reset Footer */}
            <div className="pt-2 border-t border-[#DCD8CF] flex items-center justify-between text-[11px]">
              <span className="text-[#5A6561]">
                <strong className="text-[#0D5C46]">{availableDates.length}</strong> dates with themes
              </span>
              <button
                type="button"
                onClick={() => {
                  setSelectedDateFilter("ALL");
                  setIsCalendarOpen(false);
                }}
                className="text-[#C85A32] font-bold hover:underline"
              >
                Show All Dates
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Mockups Filter Toggle */}
      <div className="flex items-center justify-between text-xs py-1 px-1">
        <label className="flex items-center gap-2 cursor-pointer text-[#1C2421] font-bold text-[11px]">
          <input
            type="checkbox"
            checked={hasMockupsOnly}
            onChange={(e) => setHasMockupsOnly(e.target.checked)}
            className="rounded text-[#C85A32] focus:ring-[#C85A32]"
          />
          <span>Show folders with mockups only</span>
        </label>
        <span className="text-[10px] text-[#5A6561] font-mono">
          {filteredFolders.length} matching
        </span>
      </div>

      {/* ── VIRTUALIZED FOLDER LIST WINDOW ────────────────────────────────────── */}
      <div
        onScroll={handleScroll}
        className="max-h-[500px] overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-[#DCD8CF]"
      >
        {isLoading ? (
          <div className="py-12 text-center text-xs text-[#5A6561] space-y-2">
            <div className="w-5 h-5 border-2 border-[#C85A32] border-t-transparent rounded-full animate-spin mx-auto" />
            <p>Loading GCS clipart folders...</p>
          </div>
        ) : visibleFolders.length > 0 ? (
          visibleFolders.map((folder) => {
            const isSelected = selectedPrefixes.includes(folder.gcs_prefix);

            return (
              <div
                key={folder.gcs_prefix}
                onClick={() => toggleSingleFolder(folder.gcs_prefix)}
                className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between gap-2 group ${
                  isSelected
                    ? "bg-[#E6F2EE] border-[#0D5C46] shadow-xs"
                    : "bg-white border-[#DCD8CF] hover:border-[#C85A32]/40 hover:bg-[#FDFCF9]"
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <div className="shrink-0">
                    {isSelected ? (
                      <CheckCircle2 className="w-4 h-4 text-[#0D5C46]" />
                    ) : (
                      <Square className="w-4 h-4 text-[#5A6561] group-hover:text-[#C85A32]" />
                    )}
                  </div>

                  <div className="truncate">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs text-[#1C2421] font-display truncate">
                        {folder.display_name}
                      </span>
                      {folder.date_folder && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-[#EFECE6] text-[#5A6561] shrink-0">
                          {folder.date_folder}
                        </span>
                      )}
                    </div>

                    <div className="text-[10px] text-[#5A6561] font-mono truncate">
                      {folder.gcs_prefix}
                    </div>
                  </div>
                </div>

                {/* Feature Badges */}
                <div className="flex items-center gap-1 shrink-0">
                  {folder.has_mockups ? (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#E6F2EE] text-[#0D5C46] border border-[#0D5C46]/30 flex items-center gap-0.5">
                      <ImageIcon className="w-2.5 h-2.5" />
                      <span>Mockups</span>
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-[#EFECE6] text-[#5A6561]">
                      No Mockups
                    </span>
                  )}

                  {folder.has_pdf && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#FDF2F2] text-[#991B1B] border border-[#F87171]/30 flex items-center gap-0.5">
                      <FileText className="w-2.5 h-2.5" />
                      <span>PDF</span>
                    </span>
                  )}

                  {folder.has_metadata && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#E6F2EE] text-[#0D5C46] flex items-center gap-0.5">
                      <Sparkles className="w-2.5 h-2.5" />
                      <span>JSON</span>
                    </span>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="py-8 text-center text-xs text-[#5A6561] space-y-1">
            <p className="font-bold text-[#1C2421]">No clipart folders match search criteria</p>
            <p className="text-[11px]">Try clearing filters or search keywords.</p>
          </div>
        )}
      </div>

      {/* ── FLOATING BATCH ACTION BAR ────────────────────────────────────────── */}
      {selectedPrefixes.length > 0 && (
        <div className="p-3 bg-[#1C2421] text-white rounded-xl shadow-xl flex items-center justify-between gap-2 animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#C85A32]" />
            <span className="text-xs font-bold">
              {selectedPrefixes.length} Theme{selectedPrefixes.length > 1 ? "s" : ""} Selected
            </span>
          </div>

          <button
            type="button"
            onClick={() => onBatchPublish && onBatchPublish(selectedFolderObjects)}
            className="px-3.5 py-1.5 bg-[#C85A32] hover:bg-[#B24D28] text-white font-bold text-xs rounded-lg transition shadow-xs cursor-pointer flex items-center gap-1"
          >
            <span>Batch Publish {selectedPrefixes.length} Theme</span>
          </button>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { usePipeline } from "@/context/PipelineContext";
import {
  Bell,
  Pause,
  Play,
  X,
  Loader2,
  CheckCircle2,
  ExternalLink,
  Layers,
  Clock,
} from "lucide-react";

/**
 * Header notification bell for pipeline status.
 *
 * Replaces the old floating popup widget. Shows a pulsing dot when a
 * pipeline is actively running. Clicking the bell opens a compact
 * dropdown with job progress, controls, and a link to /pipeline.
 */
export function PipelineNotificationBell() {
  const router = useRouter();
  const pathname = usePathname();
  const {
    isBatchRunning,
    isBatchPaused,
    batchQueue,
    activeJobIndex,
    activeJob,
    pauseBatch,
    resumeBatch,
    cancelBatch,
    hasActiveNotification,
  } = usePipeline();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const completedCount = batchQueue.filter((j) => j.status === "completed").length;
  const totalCount = batchQueue.length;
  const currentStage =
    activeJob && activeJob.stages
      ? activeJob.stages.find((s) => s.status === "running") || activeJob.stages[0]
      : null;
  const stageProgress = currentStage ? currentStage.progress_percent : 0;
  const totalProgress = activeJob ? activeJob.total_progress : 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-white text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer"
        title={hasActiveNotification ? "Pipeline running — click for details" : "Pipeline status"}
      >
        <Bell className="w-4.5 h-4.5" />
        {/* Pulsing badge dot */}
        {hasActiveNotification && (
          <span className="absolute top-1 right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#C85A32] opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#C85A32]" />
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-[#1C2421] text-white rounded-2xl shadow-2xl border border-[#0D5C46]/60 z-50 animate-in slide-in-from-top-2 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#2A3430]">
            <div className="flex items-center gap-2">
              {isBatchRunning ? (
                <Loader2 className="w-4 h-4 text-[#C85A32] animate-spin" />
              ) : isBatchPaused ? (
                <Pause className="w-4 h-4 text-yellow-400" />
              ) : (
                <Layers className="w-4 h-4 text-[#0D5C46]" />
              )}
              <span className="text-xs font-bold font-display uppercase tracking-wider text-[#EFECE6]">
                {isBatchRunning
                  ? "Pipeline Running"
                  : isBatchPaused
                  ? "Pipeline Paused"
                  : batchQueue.length > 0
                  ? "Pipeline Status"
                  : "No Active Pipeline"}
              </span>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-1.5">
              {isBatchRunning && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    pauseBatch();
                  }}
                  className="p-1 rounded-lg bg-[#5A6561]/30 hover:bg-[#5A6561]/60 text-white transition cursor-pointer"
                  title="Pause Pipeline"
                >
                  <Pause className="w-3.5 h-3.5" />
                </button>
              )}
              {isBatchPaused && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    resumeBatch();
                  }}
                  className="p-1 rounded-lg bg-[#0D5C46] hover:bg-[#094534] text-white transition cursor-pointer"
                  title="Resume Pipeline"
                >
                  <Play className="w-3.5 h-3.5" />
                </button>
              )}
              {(isBatchRunning || isBatchPaused) && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    cancelBatch();
                    setIsOpen(false);
                  }}
                  className="p-1 rounded-lg bg-[#5A6561]/30 hover:bg-red-600/40 text-gray-300 hover:text-red-400 transition cursor-pointer"
                  title="Stop Pipeline"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          {activeJob ? (
            <div className="px-4 py-3 space-y-3">
              {/* Active Theme */}
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#EFECE6] truncate font-display max-w-[210px]">
                  {activeJob.display_name}
                </span>
                <span className="font-mono text-[10px] text-[#C85A32] font-semibold bg-[#C85A32]/15 px-2 py-0.5 rounded-md">
                  {activeJobIndex >= 0 ? `${activeJobIndex + 1} / ${totalCount}` : `${completedCount}/${totalCount}`}
                </span>
              </div>

              {/* Current Stage */}
              <div className="flex items-center justify-between text-[11px] text-gray-300 font-mono">
                <span className="truncate max-w-[220px]">
                  {currentStage ? currentStage.label : "Waiting..."}
                </span>
                <span>{stageProgress}%</span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-[#1C2421] h-1.5 rounded-full overflow-hidden border border-[#2A3430]">
                <div
                  className="bg-gradient-to-r from-[#0D5C46] to-[#C85A32] h-full transition-all duration-300"
                  style={{ width: `${stageProgress}%` }}
                />
              </div>

              {/* Overall + ETA */}
              <div className="flex items-center justify-between text-[11px] text-gray-400">
                <div className="flex items-center gap-1.5">
                  <Layers className="w-3 h-3 text-[#0D5C46]" />
                  <span>Overall: {totalProgress}%</span>
                </div>
                {activeJob.estimated_eta_sec != null && activeJob.estimated_eta_sec > 0 && (
                  <div className="flex items-center gap-1 text-[#C85A32] font-semibold">
                    <Clock className="w-3 h-3" />
                    <span>
                      ETA{" "}
                      {activeJob.estimated_eta_sec < 60
                        ? `${Math.round(activeJob.estimated_eta_sec)}s`
                        : `${Math.floor(activeJob.estimated_eta_sec / 60)}m`}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : batchQueue.length > 0 ? (
            <div className="px-4 py-3">
              <div className="flex items-center gap-2 text-xs text-gray-300">
                <CheckCircle2 className="w-4 h-4 text-[#0D5C46]" />
                <span>
                  {completedCount} / {totalCount} themes completed
                </span>
              </div>
            </div>
          ) : (
            <div className="px-4 py-4 text-center">
              <p className="text-xs text-gray-400">
                No active pipeline. Start a batch from the Pipeline page.
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-[#2A3430]">
            <button
              onClick={() => {
                setIsOpen(false);
                if (pathname !== "/pipeline") {
                  router.push("/pipeline");
                }
              }}
              className="w-full flex items-center justify-center gap-1.5 text-[11px] text-[#C85A32] font-semibold hover:underline transition cursor-pointer"
            >
              <span>{pathname === "/pipeline" ? "Viewing Pipeline" : "Go to Pipeline"}</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

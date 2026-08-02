"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Layers,
  Play,
  Pause,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Terminal,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Cpu,
  ArrowRight,
  Loader2,
  FileText,
  RefreshCw,
  FolderOpen,
  Calendar,
  Hash,
  CloudOff,
  Cloud,
  Eye,
  X,
  ChevronRight,
  Power,
  PowerOff,
  Activity,
  Sparkles,
  Trash2,
  CheckSquare,
  Clock,
  ImageIcon,
} from "lucide-react";

import { usePipeline, PipelineJobItem, PipelineStageStatus } from "@/context/PipelineContext";
import { EnterpriseGcsThemeSelector, GcsFolderItem } from "@/components/gcs/EnterpriseGcsThemeSelector";

function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  return "/api/v1";
}

function formatTimeSec(seconds?: number | null): string {
  if (seconds == null || isNaN(seconds) || seconds < 0) return "--";
  const secs = Math.round(seconds);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

export default function PipelinePage() {
  const {
    gcsFolders,
    isLoadingGcs,
    fetchGcsFolders,
    comfyRunning,
    comfyStarting,
    startComfy,
    batchQueue,
    activeJobIndex,
    isBatchRunning,
    isBatchPaused,
    activeJob,
    startBatch,
    pauseBatch,
    resumeBatch,
    cancelBatch,
    clearBatch,
    retryStage,
  } = usePipeline();

  // GCS Folder Selector Selection State
  const [selectedGcsPrefixes, setSelectedGcsPrefixes] = useState<string[]>([]);
  const [expandedLogStage, setExpandedLogStage] = useState<string | null>(null);

  // Load GCS folders from session on mount (only fetches from network if session is empty)
  useEffect(() => {
    fetchGcsFolders(false);
  }, [fetchGcsFolders]);

  const handleRunBatchPipeline = (selectedFolders: GcsFolderItem[]) => {
    if (!selectedFolders.length) return;
    startBatch(selectedFolders);
  };

  const totalBatchProgress = activeJob ? activeJob.total_progress : 0;
  const completedJobsCount = batchQueue.filter((j) => j.status === "completed").length;
  const isJobFinished = activeJob ? activeJob.status === "completed" : false;

  return (
    <div className="min-h-screen bg-[#F7F6F0] flex flex-col font-sans">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <header className="bg-[#EFECE6] border-b border-[#DCD8CF] px-6 py-5 sticky top-0 z-30 shadow-xs">
        <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-2 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-white text-[#5A6561] hover:text-[#1C2421] transition shadow-xs"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>

            <div>
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-[#C85A32]/10 rounded-lg text-[#C85A32]">
                  <Layers className="w-5 h-5" />
                </div>
                <h1 className="text-xl font-bold font-display text-[#1C2421]">
                  6-Stage Execution Pipeline
                </h1>
                {isBatchRunning ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#0D5C46]/10 text-[#0D5C46] border border-[#0D5C46]/20 font-mono">
                    <Activity className="w-3 h-3 animate-pulse text-[#0D5C46]" />
                    Batch Active ({activeJobIndex + 1}/{batchQueue.length})
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-200 text-gray-700 font-mono">
                    Idle
                  </span>
                )}
              </div>
              <p className="text-xs text-[#5A6561] mt-0.5">
                Select multiple prompt folders from GCS and run sequential 6-stage AI generation with background execution.
              </p>
            </div>
          </div>

          {/* Controls Bar */}
          <div className="flex items-center gap-3">
            {/* Review Link when completed */}
            {isJobFinished && activeJob && (
              <Link
                href={`/review/${activeJob.job_id}`}
                className="px-4 py-2 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition cursor-pointer"
              >
                <span>Review & Push to Etsy</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}

            {/* ComfyUI Service Pill */}
            <div className="flex items-center gap-2 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl px-3 py-1.5 text-xs font-mono">
              <Cpu className="w-4 h-4 text-[#5A6561]" />
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${comfyRunning ? "bg-emerald-500 animate-pulse" : "bg-gray-400"}`} />
                <span className="font-bold text-[#1C2421]">
                  ComfyUI: {comfyRunning ? "ONLINE" : "OFFLINE"}
                </span>
              </div>
              {!comfyRunning && (
                <button
                  onClick={startComfy}
                  disabled={comfyStarting}
                  className="ml-2 px-2 py-0.5 bg-[#0D5C46] hover:bg-[#094534] text-white text-[10px] font-bold rounded-md transition disabled:opacity-50 cursor-pointer flex items-center gap-1"
                >
                  {comfyStarting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Power className="w-3 h-3" />}
                  <span>Start</span>
                </button>
              )}
            </div>

            {batchQueue.length > 0 && (
              <button
                onClick={clearBatch}
                className="px-3 py-1.5 bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-red-50 text-red-600 font-semibold text-xs rounded-xl transition cursor-pointer flex items-center gap-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Queue</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── MAIN CONTENT ────────────────────────────────────────────────────── */}
      <main className="max-w-[1400px] mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LEFT COLUMN: Enterprise GCS Theme Selector (5 cols) */}
        <aside className="lg:col-span-5 flex flex-col gap-4">
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#DCD8CF]">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4.5 h-4.5 text-[#C85A32]" />
                <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
                  GCS Prompt Folders
                </h2>
              </div>
              <button
                onClick={() => fetchGcsFolders(true)}
                disabled={isLoadingGcs}
                className="p-1.5 bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-white text-[#5A6561] rounded-lg transition cursor-pointer"
                title="Refresh GCS Folders from server"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingGcs ? "animate-spin" : ""}`} />
              </button>
            </div>

            <p className="text-xs text-[#5A6561]">
              Select one or multiple GCS clipart prompt folders to queue for batch execution.
            </p>

            <EnterpriseGcsThemeSelector
              folders={gcsFolders}
              selectedPrefixes={selectedGcsPrefixes}
              onSelectionChange={setSelectedGcsPrefixes}
              isLoading={isLoadingGcs}
              onBatchRunPipeline={handleRunBatchPipeline}
            />
          </div>
        </aside>

        {/* RIGHT COLUMN: Pipeline Batch Dashboard & Live Progress (7 cols) */}
        <section className="lg:col-span-7 flex flex-col gap-6">
          {/* Active Job Progress Hero Card */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-4 border-b border-[#DCD8CF]">
              <div>
                <h2 className="text-base font-bold font-display text-[#1C2421]">
                  {activeJob ? activeJob.display_name : "Batch Pipeline Queue Overview"}
                </h2>
                <p className="text-xs text-[#5A6561] mt-0.5 font-mono">
                  {activeJob ? `Job ID: ${activeJob.job_id} • ${activeJob.gcs_prefix}` : `${batchQueue.length} themes queued for batch run`}
                </p>
              </div>

              {isBatchRunning ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={pauseBatch}
                    className="px-3 py-1.5 bg-[#5A6561] hover:bg-[#47514D] text-white text-xs font-semibold rounded-xl flex items-center gap-1 transition cursor-pointer"
                  >
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause</span>
                  </button>
                  <button
                    onClick={cancelBatch}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl flex items-center gap-1 transition cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Stop</span>
                  </button>
                </div>
              ) : isBatchPaused ? (
                <button
                  onClick={resumeBatch}
                  className="px-3 py-1.5 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center gap-1 transition cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Resume Batch</span>
                </button>
              ) : null}
            </div>

            {/* Live Progress Bar & ETA Header */}
            {activeJob ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="font-bold text-[#1C2421]">
                    Stage {activeJob.stages.findIndex((s) => s.status === "running") + 1 || 1} of {activeJob.stages.length}:{" "}
                    {activeJob.stages.find((s) => s.status === "running")?.label || activeJob.stages[0]?.label}
                  </span>
                  <span className="font-bold text-[#C85A32]">{totalBatchProgress}% Overall</span>
                </div>

                <div className="w-full bg-[#DCD8CF] h-3 rounded-full overflow-hidden p-0.5">
                  <div
                    className="bg-gradient-to-r from-[#0D5C46] to-[#C85A32] h-full rounded-full transition-all duration-300"
                    style={{ width: `${totalBatchProgress}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#5A6561] font-mono">
                  <div className="flex items-center gap-3">
                    <span>Elapsed: {formatTimeSec(activeJob.elapsed_seconds)}</span>
                    {activeJob.estimated_eta_sec != null && (
                      <span className="flex items-center gap-1 text-[#C85A32] font-semibold">
                        <Clock className="w-3 h-3" />
                        ETA: {formatTimeSec(activeJob.estimated_eta_sec)}
                      </span>
                    )}
                  </div>
                  <span>Active Theme: {activeJobIndex + 1} / {batchQueue.length}</span>
                </div>
              </div>
            ) : (
              <div className="p-8 bg-[#F9F8F3] border border-dashed border-[#DCD8CF] rounded-xl text-center space-y-2">
                <Sparkles className="w-8 h-8 text-[#C85A32]/40 mx-auto" />
                <p className="text-sm font-bold text-[#1C2421]">No pipeline batch active</p>
                <p className="text-xs text-[#5A6561]">
                  Select prompt folders from the left panel and click &quot;Run Pipeline&quot; to begin.
                </p>
              </div>
            )}

            {/* 6 Stage Step Cards with Image Counts, ETA, Terminal Logs & Retry */}
            {activeJob && (
              <div className="space-y-3 pt-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {activeJob.stages.map((stg) => {
                    const isCurrent = stg.status === "running";
                    const isExpanded = expandedLogStage === stg.stage_name;

                    return (
                      <div
                        key={stg.stage_name}
                        className={`p-3.5 rounded-xl border transition ${
                          stg.status === "completed"
                            ? "bg-[#E6F2EE] border-[#0D5C46]/40 text-[#0D5C46]"
                            : isCurrent
                            ? "bg-white border-[#C85A32] text-[#1C2421] shadow-md ring-2 ring-[#C85A32]/20"
                            : stg.status === "failed"
                            ? "bg-red-50 border-red-200 text-red-700"
                            : "bg-[#F9F8F3] border-[#DCD8CF] text-[#5A6561]"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-bold font-display truncate">{stg.label}</span>
                          {stg.status === "completed" ? (
                            <CheckCircle2 className="w-4 h-4 text-[#0D5C46] shrink-0" />
                          ) : isCurrent ? (
                            <Loader2 className="w-4 h-4 text-[#C85A32] animate-spin shrink-0" />
                          ) : stg.status === "failed" ? (
                            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                          ) : (
                            <span className="w-2 h-2 rounded-full bg-gray-300 shrink-0" />
                          )}
                        </div>

                        {/* Progress bar */}
                        <div className="w-full bg-[#DCD8CF]/60 h-1.5 rounded-full overflow-hidden mb-2">
                          <div
                            className={`h-full transition-all duration-300 ${
                              stg.status === "completed"
                                ? "bg-[#0D5C46]"
                                : isCurrent
                                ? "bg-[#C85A32]"
                                : "bg-gray-300"
                            }`}
                            style={{ width: `${stg.progress_percent}%` }}
                          />
                        </div>

                        {/* Metadata row: Images Done / ETA / Terminal Toggle / Retry */}
                        <div className="flex items-center justify-between text-[10px] font-mono opacity-90">
                          <div className="flex items-center gap-2">
                            {stg.images_total > 0 && (
                              <span className="flex items-center gap-1 font-semibold">
                                <ImageIcon className="w-2.5 h-2.5" />
                                {stg.images_done} / {stg.images_total} imgs
                              </span>
                            )}
                            {stg.estimated_time_remaining_sec != null && stg.estimated_time_remaining_sec > 0 && (
                              <span>ETA {formatTimeSec(stg.estimated_time_remaining_sec)}</span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5">
                            {stg.status === "failed" && (
                              <button
                                onClick={() => activeJob && retryStage(activeJob.job_id, stg.stage_name)}
                                className="px-1.5 py-0.5 bg-red-600 text-white rounded font-bold hover:bg-red-700 transition"
                                title="Retry Failed Stage"
                              >
                                Retry
                              </button>
                            )}

                            {(stg.live_log || stg.stderr_log) && (
                              <button
                                onClick={() => setExpandedLogStage(isExpanded ? null : stg.stage_name)}
                                className="p-0.5 hover:bg-gray-200/50 rounded transition"
                                title="Toggle Terminal Output"
                              >
                                <Terminal className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Expandable Live Terminal Output / Stderr */}
                        {isExpanded && (
                          <div className="mt-2.5 p-2.5 bg-[#1C2421] text-[#EFECE6] rounded-lg font-mono text-[10px] space-y-1.5 overflow-x-auto max-h-40">
                            {stg.stderr_log && (
                              <div className="text-red-400 font-bold border-b border-red-900 pb-1">
                                [STDERR] {stg.stderr_log}
                              </div>
                            )}
                            {stg.live_log && (
                              <pre className="whitespace-pre-wrap leading-relaxed opacity-90">{stg.live_log}</pre>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Batch Job Queue List */}
          {batchQueue.length > 0 && (
            <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#DCD8CF]">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#0D5C46]" />
                  <h3 className="text-sm font-bold font-display uppercase tracking-wider text-[#1C2421]">
                    Batch Queue Items ({batchQueue.length})
                  </h3>
                </div>
                <span className="text-xs font-bold text-[#0D5C46] font-mono bg-[#E6F2EE] px-2.5 py-1 rounded-full border border-[#0D5C46]/30">
                  {completedJobsCount} / {batchQueue.length} Completed
                </span>
              </div>

              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {batchQueue.map((jobItem, qIdx) => {
                  const isActive = qIdx === activeJobIndex;
                  return (
                    <div
                      key={`${jobItem.gcs_prefix}-${qIdx}`}
                      className={`p-3.5 rounded-xl border flex items-center justify-between gap-4 transition ${
                        jobItem.status === "completed"
                          ? "bg-[#E6F2EE] border-[#0D5C46]/30"
                          : isActive
                          ? "bg-white border-[#C85A32] shadow-sm"
                          : jobItem.status === "failed"
                          ? "bg-red-50 border-red-200"
                          : "bg-[#F9F8F3] border-[#DCD8CF]"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="font-mono text-xs font-bold text-[#5A6561] shrink-0">
                          #{qIdx + 1}
                        </span>
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-[#1C2421] truncate">{jobItem.display_name}</p>
                          <p className="text-[10px] text-[#5A6561] font-mono truncate">{jobItem.gcs_prefix}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        {jobItem.status === "completed" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-[#0D5C46] text-white">
                            <CheckCircle2 className="w-3 h-3" /> Done
                          </span>
                        ) : isActive ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-[#C85A32] text-white animate-pulse">
                            <Loader2 className="w-3 h-3 animate-spin" /> Running ({jobItem.total_progress}%)
                          </span>
                        ) : jobItem.status === "failed" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-red-600 text-white">
                            Failed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-gray-200 text-gray-700">
                            Queued
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Layers,
  Play,
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
} from "lucide-react";

interface Stage {
  stage_name: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_percent: number;
  images_done?: number;
  images_total?: number;
  elapsed_seconds?: number | null;
  estimated_time_remaining_sec?: number | null;
  error_message?: string | null;
  stderr_log?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

interface PromptFile {
  name: string;
  date: string;
  theme: string;
  local_path: string | null;
  gcs_path: string;
  is_gcs?: boolean;
  preview: string;
  prompt_count: number;
  raw_text: string;
}

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

const INITIAL_STAGES: Stage[] = [
  { stage_name: "image_gen",         label: "🎨 Stage 1: Image Generation (ComfyUI)",         status: "pending", progress_percent: 0 },
  { stage_name: "bg_removal",        label: "✂️  Stage 2: Background Removal (rembg)",          status: "pending", progress_percent: 0 },
  { stage_name: "upscaling",         label: "🔍 Stage 3: AI Upscaling (Real-ESRGAN / 4×)",     status: "pending", progress_percent: 0 },
  { stage_name: "mockup_creation",   label: "🖼️  Stage 4: Mockup Creation",                    status: "pending", progress_percent: 0 },
  { stage_name: "pdf_generation",    label: "📄 Stage 5: Clickable PDF Wrap Generation",        status: "pending", progress_percent: 0 },
  { stage_name: "metadata_generation", label: "📝 Stage 6: Etsy Metadata (300 DPI & 13 Tags)", status: "pending", progress_percent: 0 },
];

interface PipelineJobData {
  job_id: string;
  user_id: string;
  theme_name: string;
  status: string;
  current_stage?: string | null;
  stages: Stage[];
  hero_image_url?: string | null;
  mockups?: string[];
  pdf_drive_link?: string | null;
  pdf_local_path?: string | null;
}

export default function PipelinePage() {
  const [vmReady] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [expandedLogStage, setExpandedLogStage] = useState<string | null>(null);
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES);
  const [jobData, setJobData] = useState<PipelineJobData | null>(null);

  // Prompt file browser state
  const [promptFiles, setPromptFiles] = useState<PromptFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [selectedFile, setSelectedFile] = useState<PromptFile | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [openDates, setOpenDates] = useState<Record<string, boolean>>({});

  // ComfyUI state
  const [comfyRunning, setComfyRunning] = useState(false);
  const [comfyStarting, setComfyStarting] = useState(false);
  const [comfyStopping, setComfyStopping] = useState(false);
  const [comfyPid, setComfyPid] = useState<number | null>(null);

  // Load prompt files from backend
  const loadPromptFiles = useCallback(async () => {
    setIsLoadingFiles(true);
    setFilesError(null);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const apiBase = getApiBaseUrl();
      let res: Response | null = null;
      try {
        res = await fetch(`${apiBase}/prompts/files`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        });
      } catch {
        if (apiBase.includes("192.168") || apiBase.includes("34.148")) {
          res = await fetch("http://localhost:8000/api/v1/prompts/files", {
            headers: { Authorization: token ? `Bearer ${token}` : "" },
          });
        }
      }
      if (res && res.ok) {
        const data = await res.json();
        setPromptFiles(data.files || []);
      } else {
        setFilesError("Could not load prompt files from server.");
      }
    } catch {
      setFilesError("Backend unreachable. Save a prompt file first.");
    } finally {
      setIsLoadingFiles(false);
    }
  }, []);

  useEffect(() => {
    loadPromptFiles();
  }, [loadPromptFiles]);

  // Poll ComfyUI status every 8 seconds
  const checkComfyStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(`${getApiBaseUrl()}/pipeline/comfyui/status`, {
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        const data = await res.json();
        setComfyRunning(data.running);
        setComfyPid(data.pid ?? null);
      }
    } catch {
      // Backend not reachable yet — ignore silently
    }
  }, []);

  useEffect(() => {
    checkComfyStatus();
    const interval = setInterval(checkComfyStatus, 8000);
    return () => clearInterval(interval);
  }, [checkComfyStatus]);

  const handleStartComfy = async () => {
    setComfyStarting(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(`${getApiBaseUrl()}/pipeline/comfyui/start`, {
        method: "POST",
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "started" || data.status === "already_running") {
          setComfyRunning(true);
        }
        // Poll again after a short wait to pick up "starting" state
        setTimeout(checkComfyStatus, 4000);
      }
    } catch {
      alert("Could not reach backend to start ComfyUI.");
    } finally {
      setComfyStarting(false);
    }
  };

  const handleStopComfy = async () => {
    setComfyStopping(true);
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(`${getApiBaseUrl()}/pipeline/comfyui/stop`, {
        method: "POST",
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        setComfyRunning(false);
        setComfyPid(null);
      }
    } catch {
      alert("Could not reach backend to stop ComfyUI.");
    } finally {
      setComfyStopping(false);
    }
  };

  const pollJobProgress = (id: string) => {
    setJobId(id);
    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem("craftdesk_access_token");
        const res = await fetch(`${getApiBaseUrl()}/pipeline/jobs/${id}`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        });
        if (res.ok) {
          const data: PipelineJobData = await res.json();
          setJobData(data);
          if (data.stages && data.stages.length > 0) {
            setStages(data.stages);
          }
          if (data.status === "completed") {
            setJobStatus("completed");
            clearInterval(interval);
          } else if (data.status === "failed") {
            setJobStatus("failed");
            clearInterval(interval);
          }
        }
      } catch {
        // Continue polling if transient network error
      }
    }, 1000);
  };

  const handleStartPipeline = async () => {
    if (!selectedFile) return;
    setJobStatus("running");
    setStages(INITIAL_STAGES.map((s) => ({ ...s, status: "pending", progress_percent: 0 })));
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch(`${getApiBaseUrl()}/pipeline/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: token ? `Bearer ${token}` : "" },
        body: JSON.stringify({
          theme_name: selectedFile.theme,
          prompt_file_path: selectedFile.gcs_path || selectedFile.local_path,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setJobId(data.job_id);
        pollJobProgress(data.job_id);
      } else {
        throw new Error("Failed to start pipeline job");
      }
    } catch {
      alert("Error starting pipeline execution. Check backend API status.");
      setJobStatus("idle");
    }
  };

  const handleStopPipeline = async () => {
    if (!jobId) return;
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      await fetch(`${getApiBaseUrl()}/pipeline/jobs/${jobId}/stop`, {
        method: "POST",
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
    } catch {
      // Ignore network errors on stop
    } finally {
      setJobStatus("failed");
    }
  };

  const handleSimulateFailure = () => {
    setStages((prev) => {
      const next = [...prev];
      next[0] = { ...next[0], status: "completed", progress_percent: 100 };
      next[1] = { ...next[1], status: "completed", progress_percent: 100 };
      next[2] = {
        ...next[2], status: "failed", progress_percent: 50,
        error_message: "RuntimeError in upscaling_worker: CUDA Out of Memory (OOM) on tile 4/16.",
        stderr_log: "Traceback (most recent call last):\n  File 'etsy_pipeline/workers/upscale_worker.py', line 54, in run\n    torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.40 GiB.",
      };
      return next;
    });
    setJobStatus("failed");
  };

  const handleRetryStage = (stageName: string) => {
    setStages((prev) =>
      prev.map((s) =>
        s.stage_name === stageName
          ? { ...s, status: "running", progress_percent: 25, error_message: null, stderr_log: null }
          : s
      )
    );
    setTimeout(() => {
      setStages((prev) =>
        prev.map((s) =>
          s.stage_name === stageName ? { ...s, status: "completed", progress_percent: 100 } : s
        )
      );
      setJobStatus("running");
      simulatePipelineProgress(jobId || "demo-job-1");
    }, 1500);
  };

  const resetPipeline = () => {
    setStages(INITIAL_STAGES.map((s) => ({ ...s, status: "pending", progress_percent: 0 })));
    setJobStatus("idle");
    setJobId(null);
  };

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#DCD8CF] bg-[#EFECE6]/90 sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-2 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421] transition"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-[#0D5C46]" />
              <h1 className="font-bold text-lg font-display text-[#1C2421]">
                6-Stage Asset Pipeline
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* ComfyUI start/stop control */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] text-xs">
              <Activity className={`w-3.5 h-3.5 ${comfyRunning ? "text-[#0D5C46] animate-pulse" : "text-[#5A6561]"}`} />
              <span className="text-[#5A6561]">ComfyUI:</span>
              {comfyRunning ? (
                <span className="font-bold text-[#0D5C46]">
                  Running ✅{comfyPid ? ` (PID ${comfyPid})` : " (:8188)"}
                </span>
              ) : (
                <span className="font-bold text-amber-600">Stopped ⚠️</span>
              )}
            </div>

            {comfyRunning ? (
              <button
                onClick={handleStopComfy}
                disabled={comfyStopping}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
              >
                {comfyStopping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PowerOff className="w-3.5 h-3.5" />}
                <span>Stop ComfyUI</span>
              </button>
            ) : (
              <button
                onClick={handleStartComfy}
                disabled={comfyStarting}
                className="px-3 py-1.5 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
              >
                {comfyStarting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Power className="w-3.5 h-3.5" />}
                <span>{comfyStarting ? "Starting…" : "Start ComfyUI"}</span>
              </button>
            )}

            {jobStatus === "completed" && (
              <Link
                href={`/review/${jobId || "demo-job-1"}`}
                className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-medium text-xs rounded-xl shadow-sm flex items-center gap-2 transition"
              >
                <span>Review & Push to Etsy</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main layout: left panel + right pipeline */}
      <main className="max-w-[1400px] mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* ── LEFT PANEL: Prompt File Browser ── */}
        <aside className="lg:col-span-4 flex flex-col gap-4">

          {/* Panel header */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl shadow-sm overflow-hidden flex flex-col" style={{ maxHeight: "calc(100vh - 140px)" }}>
            <div className="px-5 py-4 border-b border-[#DCD8CF] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-[#C85A32]" />
                <h2 className="text-sm font-bold uppercase tracking-wider font-display text-[#1C2421]">
                  Prompt Files
                </h2>
                {promptFiles.length > 0 && (
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-[#C85A32]/10 text-[#C85A32] rounded-full">
                    {promptFiles.length}
                  </span>
                )}
              </div>
              <button
                onClick={loadPromptFiles}
                disabled={isLoadingFiles}
                title="Refresh file list"
                className="p-1.5 rounded-lg hover:bg-[#DCD8CF]/60 text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer disabled:opacity-40"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingFiles ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="px-4 pt-3 pb-2 shrink-0">
              <p className="text-[11px] text-[#5A6561] leading-relaxed">
                Select a prompt file to load its prompts and run the pipeline below.
              </p>
            </div>

            {/* File list */}
            <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-2">
              {isLoadingFiles ? (
                <div className="flex items-center justify-center h-32 gap-2 text-[#5A6561]">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-xs">Loading files…</span>
                </div>
              ) : filesError ? (
                <div className="mt-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <CloudOff className="w-3.5 h-3.5" />
                    <span>No files found</span>
                  </div>
                  <p className="opacity-80">{filesError}</p>
                  <Link href="/prompt-studio" className="text-[#C85A32] font-semibold hover:underline flex items-center gap-1">
                    <span>Go to Prompt Studio</span>
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              ) : promptFiles.length === 0 ? (
                <div className="mt-3 p-5 bg-[#F9F8F3] border border-dashed border-[#DCD8CF] rounded-xl text-center space-y-2">
                  <FileText className="w-8 h-8 text-[#DCD8CF] mx-auto" />
                  <p className="text-xs font-semibold text-[#5A6561]">No prompt files saved yet</p>
                  <p className="text-[11px] text-[#5A6561]/70">Generate and save prompts in the Prompt Studio first.</p>
                  <Link
                    href="/prompt-studio"
                    className="inline-flex items-center gap-1 text-[11px] text-[#C85A32] font-semibold hover:underline mt-1"
                  >
                    Open Prompt Studio <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              ) : (
                Object.entries(
                  promptFiles.reduce<Record<string, PromptFile[]>>((acc, file) => {
                    const dateKey = file.date || "Unknown Date";
                    if (!acc[dateKey]) acc[dateKey] = [];
                    acc[dateKey].push(file);
                    return acc;
                  }, {})
                ).map(([dateStr, filesInDate]) => {
                  const isOpen = openDates[dateStr] !== false;
                  return (
                    <div key={dateStr} className="space-y-1.5 mb-3">
                      {/* Date Folder Header */}
                      <button
                        onClick={() =>
                          setOpenDates((prev) => ({
                            ...prev,
                            [dateStr]: prev[dateStr] === false ? true : false,
                          }))
                        }
                        className="w-full flex items-center justify-between px-3 py-2 bg-[#E5E0D8] border border-[#DCD8CF] rounded-xl hover:bg-[#DCD8CF]/60 transition cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          {isOpen ? (
                            <ChevronDown className="w-3.5 h-3.5 text-[#C85A32]" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-[#5A6561]" />
                          )}
                          <FolderOpen className="w-3.5 h-3.5 text-[#C85A32]" />
                          <span className="text-xs font-bold text-[#1C2421]">{dateStr}</span>
                        </div>
                        <span className="text-[10px] font-bold text-[#5A6561] bg-[#DCD8CF] px-2 py-0.5 rounded-full">
                          {filesInDate.length} {filesInDate.length === 1 ? "theme" : "themes"}
                        </span>
                      </button>

                      {/* Theme Files Inside Date Folder */}
                      {isOpen && (
                        <div className="pl-3 space-y-1.5 border-l-2 border-[#DCD8CF] ml-2.5">
                          {filesInDate.map((file, idx) => {
                            const isSelected = selectedFile?.gcs_path === file.gcs_path;
                            return (
                              <button
                                key={`${file.gcs_path}-${idx}`}
                                onClick={() => {
                                  setSelectedFile(file);
                                  resetPipeline();
                                }}
                                className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                                  isSelected
                                    ? "bg-[#0D5C46] border-[#0D5C46] text-white shadow-md"
                                    : "bg-[#F9F8F3] border-[#DCD8CF] hover:border-[#0D5C46]/50 hover:bg-[#EFECE6]"
                                }`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex items-center gap-2 min-w-0">
                                    <FileText className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-white/80" : "text-[#C85A32]"}`} />
                                    <span className={`text-xs font-bold truncate ${isSelected ? "text-white" : "text-[#1C2421]"}`}>
                                      {file.name}
                                    </span>
                                  </div>
                                  {isSelected && (
                                    <span className="shrink-0 text-[10px] bg-white/20 text-white font-semibold px-1.5 py-0.5 rounded-md">
                                      Selected
                                    </span>
                                  )}
                                </div>

                                <div className={`flex items-center gap-3 mt-1.5 text-[10px] ${isSelected ? "text-white/70" : "text-[#5A6561]"}`}>
                                  <span className="flex items-center gap-1">
                                    <Calendar className="w-2.5 h-2.5" />
                                    {file.date}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Hash className="w-2.5 h-2.5" />
                                    {file.prompt_count} prompts
                                  </span>
                                  <span className="flex items-center gap-1">
                                    {file.is_gcs !== false ? (
                                      <><Cloud className="w-2.5 h-2.5" />GCS</>
                                    ) : (
                                      <><FileText className="w-2.5 h-2.5" />Local</>
                                    )}
                                  </span>
                                </div>

                                <p className={`mt-2 text-[10px] leading-relaxed line-clamp-2 ${isSelected ? "text-white/60" : "text-[#5A6561]"}`}>
                                  {file.preview}
                                </p>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Selected file detail card */}
          {selectedFile && (
            <div className="bg-[#EFECE6] border border-[#0D5C46]/40 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#0D5C46]" />
                  <span className="text-xs font-bold text-[#0D5C46]">Ready to Run</span>
                </div>
                <button
                  onClick={() => setPreviewOpen(true)}
                  className="text-[11px] text-[#C85A32] font-semibold hover:underline flex items-center gap-1"
                >
                  <Eye className="w-3 h-3" />
                  Preview Prompts
                </button>
              </div>

              <div>
                <p className="text-xs font-bold text-[#1C2421] truncate">{selectedFile.name}</p>
                <p className="text-[11px] text-[#5A6561] mt-0.5 font-mono break-all leading-relaxed">
                  {selectedFile.gcs_path}
                </p>
              </div>

              <div className="flex gap-2 text-[10px] text-[#5A6561]">
                <span className="px-2 py-1 bg-[#F9F8F3] border border-[#DCD8CF] rounded-lg">{selectedFile.date}</span>
                <span className="px-2 py-1 bg-[#F9F8F3] border border-[#DCD8CF] rounded-lg">{selectedFile.prompt_count} prompts</span>
                <span className={`px-2 py-1 rounded-lg border ${selectedFile.is_gcs !== false ? "bg-blue-50 border-blue-200 text-blue-700" : "bg-[#E6F2EE] border-[#0D5C46]/30 text-[#0D5C46]"}`}>
                  {selectedFile.is_gcs !== false ? "☁️ GCS" : "💾 Local"}
                </span>
              </div>
            </div>
          )}
        </aside>

        {/* ── RIGHT PANEL: Pipeline Runner ── */}
        <div className="lg:col-span-8 flex flex-col gap-6">

          {/* Control bar */}
          <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold font-display text-[#1C2421]">Pipeline Runner</h2>
                {selectedFile ? (
                  <p className="text-xs text-[#0D5C46] mt-1 font-medium flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    Running for: <span className="font-bold">{selectedFile.name}</span>
                    <span className="text-[#5A6561]">({selectedFile.prompt_count} prompts)</span>
                  </p>
                ) : (
                  <p className="text-xs text-amber-600 mt-1 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Select a prompt file from the left panel to enable the pipeline.
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3">
                {jobStatus !== "idle" && (
                  <button
                    onClick={handleSimulateFailure}
                    className="px-3 py-2 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-xl hover:bg-red-100 transition cursor-pointer"
                    title="Test error card & retry state"
                  >
                    Simulate Failure
                  </button>
                )}

                {jobStatus === "running" && (
                  <button
                    onClick={handleStopPipeline}
                    className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-semibold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer"
                    title="Stop/cancel running pipeline job"
                  >
                    <PowerOff className="w-4 h-4" />
                    <span>Stop Execution</span>
                  </button>
                )}

                <button
                  onClick={handleStartPipeline}
                  disabled={jobStatus === "running" || !selectedFile}
                  className="px-5 py-2.5 bg-[#0D5C46] hover:bg-[#094534] text-white font-semibold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer disabled:opacity-50"
                >
                  {jobStatus === "running" ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Executing Pipeline…</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" />
                      <span>{selectedFile ? `Run Pipeline — ${selectedFile.name}` : "Select a Prompt File First"}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Active prompt file mini-bar */}
            {selectedFile && jobStatus !== "idle" && (
              <div className="mt-4 pt-4 border-t border-[#DCD8CF] flex items-center gap-3">
                <div className="flex-1 bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl px-3 py-2 font-mono text-[11px] text-[#5A6561] truncate">
                  {selectedFile.gcs_path}
                </div>
                {jobId && (
                  <span className="text-[10px] font-mono text-[#5A6561] shrink-0">
                    Job: <span className="text-[#1C2421] font-bold">{jobId}</span>
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Stage cards */}
          <div className="space-y-4">
            {stages.map((stage, idx) => (
              <div
                key={stage.stage_name}
                className={`p-5 rounded-2xl border transition shadow-sm ${
                  stage.status === "failed"
                    ? "bg-red-50/70 border-red-300"
                    : stage.status === "running"
                    ? "bg-[#F9F8F3] border-[#0D5C46]"
                    : stage.status === "completed"
                    ? "bg-[#EFECE6] border-[#DCD8CF]"
                    : "bg-[#EFECE6]/60 border-[#DCD8CF]/60 opacity-70"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3.5">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                        stage.status === "completed"
                          ? "bg-[#E6F2EE] text-[#0D5C46]"
                          : stage.status === "failed"
                          ? "bg-red-100 text-red-600"
                          : stage.status === "running"
                          ? "bg-[#0D5C46] text-white"
                          : "bg-[#F9F8F3] text-[#5A6561]"
                      }`}
                    >
                      {stage.status === "completed" ? <CheckCircle2 className="w-4 h-4" /> : idx + 1}
                    </div>
                    <div>
                      <h3 className="font-bold text-sm text-[#1C2421] font-display">{stage.label}</h3>
                      {stage.completed_at ? (
                        <p className="text-[11px] text-[#0D5C46] font-medium mt-0.5">
                          Completed at {new Date(stage.completed_at).toLocaleTimeString()}
                          {stage.elapsed_seconds != null && ` (${formatTimeSec(stage.elapsed_seconds)})`}
                        </p>
                      ) : stage.status === "running" ? (
                        <div className="flex items-center gap-3 mt-1 text-[11px] text-[#5A6561]">
                          {stage.images_total != null && stage.images_total > 0 && (
                            <span className="font-semibold text-[#0D5C46]">
                              {stage.images_done ?? 0} / {stage.images_total} items
                            </span>
                          )}
                          {stage.elapsed_seconds != null && (
                            <span>Elapsed: {formatTimeSec(stage.elapsed_seconds)}</span>
                          )}
                          {stage.estimated_time_remaining_sec != null && stage.estimated_time_remaining_sec > 0 && (
                            <span className="font-semibold text-amber-700">
                              ETA ~ {formatTimeSec(stage.estimated_time_remaining_sec)}
                            </span>
                          )}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {stage.status === "pending" && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-[#F9F8F3] border border-[#DCD8CF] text-[#5A6561]">
                        ⏳ Pending
                      </span>
                    )}
                    {stage.status === "running" && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-[#E6F2EE] text-[#0D5C46] border border-[#0D5C46]/30 flex items-center gap-1.5 animate-pulse">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Running ({stage.progress_percent}%)</span>
                      </span>
                    )}
                    {stage.status === "completed" && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-[#E6F2EE] text-[#0D5C46] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Completed ✅
                      </span>
                    )}
                    {stage.status === "failed" && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                        Failed ❌
                      </span>
                    )}
                  </div>
                </div>

                {stage.status === "running" && (
                  <div className="mt-4 space-y-1">
                    <div className="w-full bg-[#DCD8CF]/50 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-[#0D5C46] h-full rounded-full transition-all duration-300"
                        style={{ width: `${Math.max(5, stage.progress_percent)}%` }}
                      />
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-[#5A6561]">
                      <span>Progress: {stage.progress_percent}%</span>
                      {stage.estimated_time_remaining_sec != null && stage.estimated_time_remaining_sec > 0 && (
                        <span>Est. Remaining: {formatTimeSec(stage.estimated_time_remaining_sec)}</span>
                      )}
                    </div>
                  </div>
                )}

                {stage.status === "completed" && stage.stage_name === "mockup_creation" && (
                  <div className="mt-4 pt-3 border-t border-[#DCD8CF]/60 space-y-2">
                    <p className="text-xs font-bold text-[#0D5C46] flex items-center gap-1.5">
                      <Eye className="w-3.5 h-3.5" />
                      Generated Mockup Previews:
                    </p>
                    {jobData?.mockups && jobData.mockups.length > 0 ? (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                        {jobData.mockups.slice(0, 4).map((url, i) => (
                          <div key={i} className="aspect-square bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl overflow-hidden shadow-xs relative group">
                            <img src={url} alt={`Mockup ${i + 1}`} className="w-full h-full object-cover group-hover:scale-105 transition" />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-[#5A6561] italic">
                        4 Etsy product mockups (Hero.png, grid, style preview) generated in local output directory.
                      </p>
                    )}
                  </div>
                )}

                {stage.status === "completed" && stage.stage_name === "pdf_generation" && (
                  <div className="mt-4 pt-3 border-t border-[#DCD8CF]/60 space-y-3">
                    <p className="text-xs font-bold text-[#0D5C46] flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" />
                      Clickable PDF Download Bundle Ready:
                    </p>
                    <div className="flex flex-wrap items-center gap-3">
                      {jobData?.pdf_drive_link && (
                        <a
                          href={jobData.pdf_drive_link}
                          target="_blank"
                          rel="noreferrer"
                          className="px-3.5 py-2 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-sm transition"
                        >
                          <Cloud className="w-3.5 h-3.5" />
                          <span>Open Google Drive Clipart Bundle 🔗</span>
                        </a>
                      )}

                      {jobId && (
                        <a
                          href={`${getApiBaseUrl()}/pipeline/jobs/${jobId}/pdf`}
                          download
                          className="px-3.5 py-2 bg-[#F9F8F3] hover:bg-white text-[#1C2421] border border-[#DCD8CF] text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow-xs"
                        >
                          <FileText className="w-3.5 h-3.5 text-[#C85A32]" />
                          <span>Download A4 Catalog PDF 💾</span>
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {stage.status === "failed" && (
                  <div className="mt-4 pt-4 border-t border-red-200 space-y-3">
                    <div className="p-3 bg-red-100/70 border border-red-200 rounded-xl text-xs text-red-900 font-mono flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <strong className="block text-[11px] uppercase tracking-wider text-red-700 font-sans mb-0.5">
                          Root Exception:
                        </strong>
                        <span>{stage.error_message || "Stage execution failed."}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <button
                        onClick={() =>
                          setExpandedLogStage(expandedLogStage === stage.stage_name ? null : stage.stage_name)
                        }
                        className="text-xs text-red-700 hover:text-red-900 font-semibold flex items-center gap-1 cursor-pointer"
                      >
                        <Terminal className="w-3.5 h-3.5" />
                        <span>{expandedLogStage === stage.stage_name ? "Hide Stderr Log" : "View Stderr Log"}</span>
                        {expandedLogStage === stage.stage_name ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      <button
                        onClick={() => handleRetryStage(stage.stage_name)}
                        className="px-3 py-1.5 bg-[#C85A32] hover:bg-[#B24D28] text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow-sm cursor-pointer"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Retry Stage</span>
                      </button>
                    </div>

                    {expandedLogStage === stage.stage_name && stage.stderr_log && (
                      <pre className="p-3.5 bg-slate-900 text-slate-100 rounded-xl text-[11px] font-mono overflow-x-auto border border-slate-800 leading-relaxed">
                        {stage.stderr_log}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* ── Full Prompt Preview Modal ── */}
      {previewOpen && selectedFile && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6"
          onClick={() => setPreviewOpen(false)}
        >
          <div
            className="bg-[#F7F6F0] border border-[#DCD8CF] rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#DCD8CF] shrink-0">
              <div>
                <h3 className="font-bold text-base font-display text-[#1C2421]">{selectedFile.name}</h3>
                <p className="text-[11px] text-[#5A6561] mt-0.5">
                  {selectedFile.prompt_count} prompts · {selectedFile.date} · {selectedFile.gcs_path}
                </p>
              </div>
              <button
                onClick={() => setPreviewOpen(false)}
                className="p-2 rounded-xl hover:bg-[#EFECE6] text-[#5A6561] hover:text-[#1C2421] transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <pre className="whitespace-pre-wrap font-mono text-xs text-[#1C2421] leading-relaxed bg-[#1C2421] text-[#EFECE6] p-5 rounded-xl">
                {selectedFile.raw_text}
              </pre>
            </div>
            <div className="px-6 py-4 border-t border-[#DCD8CF] shrink-0 flex justify-between items-center">
              <span className="text-[11px] text-[#5A6561]">Click outside or press × to close</span>
              <button
                onClick={() => { setPreviewOpen(false); }}
                className="px-4 py-2 bg-[#0D5C46] hover:bg-[#094534] text-white text-xs font-semibold rounded-xl transition"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

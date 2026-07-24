"use client";

import React, { useState, useEffect } from "react";
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
  Sparkles,
} from "lucide-react";

interface Stage {
  stage_name: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_percent: number;
  error_message?: string | null;
  stderr_log?: string | null;
  completed_at?: string | null;
}

export default function PipelinePage() {
  const [vmReady, setVmReady] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [expandedLogStage, setExpandedLogStage] = useState<string | null>(null);

  const [stages, setStages] = useState<Stage[]>([
    { stage_name: "image_gen", label: "🎨 Stage 1: Image Generation (ComfyUI)", status: "pending", progress_percent: 0 },
    { stage_name: "bg_removal", label: "✂️ Stage 2: Background Removal (rembg)", status: "pending", progress_percent: 0 },
    { stage_name: "upscaling", label: "🔍 Stage 3: AI Upscaling (Real-ESRGAN / 4x)", status: "pending", progress_percent: 0 },
    { stage_name: "mockup_creation", label: "🖼️ Stage 4: Mockup Creation (etsy mockup creator)", status: "pending", progress_percent: 0 },
    { stage_name: "pdf_generation", label: "📄 Stage 5: Clickable PDF Wrap Generation", status: "pending", progress_percent: 0 },
    { stage_name: "metadata_generation", label: "📝 Stage 6: Etsy Metadata (300 DPI & 13 Tags)", status: "pending", progress_percent: 0 },
  ]);

  const handleStartPipeline = async () => {
    setJobStatus("running");
    try {
      const token = localStorage.getItem("craftdesk_access_token");
      const res = await fetch("http://localhost:8000/api/v1/pipeline/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          theme_name: "Wonder Woman Birthday Watercolor",
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setJobId(data.job_id);
        simulatePipelineProgress(data.job_id);
      } else {
        throw new Error("Failed to start job");
      }
    } catch {
      // Demo progress simulation
      simulatePipelineProgress("demo-job-1");
    }
  };

  const simulatePipelineProgress = (id: string) => {
    setJobId(id);
    let currentStep = 0;

    const interval = setInterval(() => {
      setStages((prev) => {
        const next = [...prev];
        if (currentStep < next.length) {
          // Set previous completed
          for (let i = 0; i < currentStep; i++) {
            next[i].status = "completed";
            next[i].progress_percent = 100;
          }
          // Set current running
          next[currentStep].status = "running";
          next[currentStep].progress_percent = 65;
          currentStep++;
        } else {
          // All completed
          for (let i = 0; i < next.length; i++) {
            next[i].status = "completed";
            next[i].progress_percent = 100;
          }
          setJobStatus("completed");
          clearInterval(interval);
        }
        return next;
      });
    }, 1200);
  };

  const handleSimulateFailure = () => {
    setStages((prev) => {
      const next = [...prev];
      next[0].status = "completed";
      next[0].progress_percent = 100;
      next[1].status = "completed";
      next[1].progress_percent = 100;
      next[2].status = "failed";
      next[2].progress_percent = 50;
      next[2].error_message = "RuntimeError in upscaling_worker: CUDA Out of Memory (OOM) on tile 4/16.";
      next[2].stderr_log = "Traceback (most recent call last):\n  File 'etsy_pipeline/workers/upscale_worker.py', line 54, in run\n    torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.40 GiB.";
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
          s.stage_name === stageName
            ? { ...s, status: "completed", progress_percent: 100 }
            : s
        )
      );
      setJobStatus("running");
      simulatePipelineProgress(jobId || "demo-job-1");
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-[#F7F6F0] text-[#1C2421] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#DCD8CF] bg-[#EFECE6]/90 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
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
            {/* GPU VM Status indicator */}
            <div className="px-3 py-1.5 rounded-xl bg-[#F9F8F3] border border-[#DCD8CF] flex items-center gap-2 text-xs">
              <Cpu className="w-3.5 h-3.5 text-[#0D5C46]" />
              <span className="text-[#5A6561]">GPU VM:</span>
              <span className="font-bold text-[#0D5C46]">Ready ✅ (:8188)</span>
            </div>

            {jobStatus === "completed" && (
              <Link
                href={`/review/${jobId || "demo-job-1"}`}
                className="px-4 py-2 bg-[#C85A32] hover:bg-[#B24D28] text-white font-medium text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer"
              >
                <span>Review & Push to Etsy</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Top Control Bar */}
        <div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold font-display text-[#1C2421]">
              Pipeline Runner
            </h2>
            <p className="text-xs text-[#5A6561] mt-1">
              Executes Image Gen, BG Remove, 4x Upscaling, Mockups, PDF, and 300 DPI Metadata.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSimulateFailure}
              className="px-3 py-2 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-xl hover:bg-red-100 transition cursor-pointer"
              title="Test error card & retry state"
            >
              Simulate Failure
            </button>
            <button
              onClick={handleStartPipeline}
              disabled={jobStatus === "running"}
              className="px-5 py-2.5 bg-[#0D5C46] hover:bg-[#094534] text-white font-semibold text-xs rounded-xl shadow-sm flex items-center gap-2 transition cursor-pointer disabled:opacity-60"
            >
              {jobStatus === "running" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Run CraftDesk Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 6 Stage Cards Grid */}
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
                    className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
                      stage.status === "completed"
                        ? "bg-[#E6F2EE] text-[#0D5C46]"
                        : stage.status === "failed"
                        ? "bg-red-100 text-red-600"
                        : stage.status === "running"
                        ? "bg-[#0D5C46] text-white"
                        : "bg-[#F9F8F3] text-[#5A6561]"
                    }`}
                  >
                    {idx + 1}
                  </div>

                  <div>
                    <h3 className="font-bold text-sm text-[#1C2421] font-display">
                      {stage.label}
                    </h3>
                    {stage.completed_at && (
                      <p className="text-[11px] text-[#0D5C46] font-medium mt-0.5">
                        Completed at {new Date(stage.completed_at).toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                </div>

                {/* Status Badges */}
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

              {/* Progress Bar for Running state */}
              {stage.status === "running" && (
                <div className="mt-4 w-full bg-[#DCD8CF]/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-[#0D5C46] h-full rounded-full transition-all duration-300"
                    style={{ width: `${stage.progress_percent}%` }}
                  />
                </div>
              )}

              {/* Failure State Expansion */}
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
                        setExpandedLogStage(
                          expandedLogStage === stage.stage_name ? null : stage.stage_name
                        )
                      }
                      className="text-xs text-red-700 hover:text-red-900 font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <Terminal className="w-3.5 h-3.5" />
                      <span>{expandedLogStage === stage.stage_name ? "Hide Stderr Log" : "View Stderr Log"}</span>
                      {expandedLogStage === stage.stage_name ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
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
      </main>
    </div>
  );
}

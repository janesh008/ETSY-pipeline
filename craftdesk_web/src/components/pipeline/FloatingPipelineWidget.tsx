"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { usePipeline } from "@/context/PipelineContext";
import { Play, Pause, X, ExternalLink, Activity, Layers, Move } from "lucide-react";

export function FloatingPipelineWidget() {
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
    showFloatingWidget,
    dismissFloatingWidget,
  } = usePipeline();

  // Draggable widget state
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 24, y: 24 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ mouseX: number; mouseY: number; startX: number; startY: number }>({
    mouseX: 0,
    mouseY: 0,
    startX: 24,
    startY: 24,
  });

  // Handle Dragging Callbacks (All hooks defined at top before any returns)
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      startX: position.x,
      startY: position.y,
    };
  };

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = dragStartRef.current.mouseX - e.clientX;
      const deltaY = dragStartRef.current.mouseY - e.clientY;

      const newX = Math.max(12, Math.min(window.innerWidth - 380, dragStartRef.current.startX + deltaX));
      const newY = Math.max(12, Math.min(window.innerHeight - 200, dragStartRef.current.startY + deltaY));

      setPosition({ x: newX, y: newY });
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      return () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Hide widget if explicitly dismissed, or if no active batch is running/paused and queue is empty
  if (!showFloatingWidget || (!isBatchRunning && !isBatchPaused && batchQueue.length === 0)) {
    return null;
  }

  const completedCount = batchQueue.filter((j) => j.status === "completed").length;
  const totalCount = batchQueue.length;
  const currentStage = activeJob && activeJob.stages ? activeJob.stages.find((s) => s.status === "running") || activeJob.stages[0] : null;

  const stageProgress = currentStage ? currentStage.progress_percent : 0;
  const stageName = currentStage ? currentStage.label || currentStage.stage_name : "Batch Queued";
  const totalProgress = activeJob ? activeJob.total_progress : 0;

  const handleWidgetClick = () => {
    if (pathname !== "/pipeline") {
      router.push("/pipeline");
    }
  };

  return (
    <div
      style={{ right: `${position.x}px`, bottom: `${position.y}px` }}
      className="fixed z-50 animate-in slide-in-from-bottom-5 duration-300 select-none"
    >
      <div
        onClick={handleWidgetClick}
        className={`w-96 p-4 bg-[#1C2421] text-white rounded-2xl shadow-2xl border transition group ${
          isDragging ? "cursor-grabbing border-[#C85A32] ring-2 ring-[#C85A32]/40" : "cursor-pointer border-[#0D5C46]/60 hover:border-[#C85A32]"
        }`}
      >
        {/* Top Header (Drag Handle) */}
        <div
          onMouseDown={handleMouseDown}
          className="flex items-center justify-between pb-2 border-b border-[#2A3430] cursor-grab"
        >
          <div className="flex items-center gap-2">
            <Move className="w-3.5 h-3.5 text-[#5A6561] group-hover:text-white transition" />
            <Activity className="w-4 h-4 text-[#C85A32] animate-pulse" />
            <span className="text-xs font-bold font-display uppercase tracking-wider text-[#EFECE6]">
              {isBatchRunning ? "Pipeline Running" : isBatchPaused ? "Pipeline Paused" : "Batch Finished"}
            </span>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            {isBatchRunning ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  pauseBatch();
                }}
                className="p-1 rounded-lg bg-[#5A6561]/30 hover:bg-[#5A6561]/60 text-white transition cursor-pointer"
                title="Pause Pipeline"
              >
                <Pause className="w-3.5 h-3.5" />
              </button>
            ) : isBatchPaused ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  resumeBatch();
                }}
                className="p-1 rounded-lg bg-[#0D5C46] hover:bg-[#094534] text-white transition cursor-pointer"
                title="Resume Pipeline"
              >
                <Play className="w-3.5 h-3.5" />
              </button>
            ) : null}

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                dismissFloatingWidget();
              }}
              className="p-1 rounded-lg bg-[#5A6561]/30 hover:bg-red-600/40 text-gray-300 hover:text-red-400 transition cursor-pointer"
              title="Close Widget"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Current Active Theme Details */}
        <div className="bg-[#2A3430] p-3 rounded-xl border border-[#3A4641] space-y-2 mt-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-[#EFECE6] truncate font-display max-w-[210px]">
              {activeJob ? activeJob.display_name : "All Themes Completed"}
            </span>
            <span className="font-mono text-[10px] text-[#C85A32] font-semibold bg-[#C85A32]/15 px-2 py-0.5 rounded-md">
              {activeJobIndex >= 0 ? `${activeJobIndex + 1} / ${totalCount}` : `${completedCount}/${totalCount}`}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-gray-300 font-mono">
            <span className="truncate max-w-[220px]">{stageName}</span>
            <span>{stageProgress}%</span>
          </div>

          {/* Active Stage Progress Bar */}
          <div className="w-full bg-[#1C2421] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#0D5C46] to-[#C85A32] h-full transition-all duration-300"
              style={{ width: `${stageProgress}%` }}
            />
          </div>
        </div>

        {/* Footer info banner */}
        <div className="flex items-center justify-between text-[11px] text-gray-400 mt-2">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#0D5C46]" />
            <span>Overall: {totalProgress}%</span>
          </div>

          <div className="flex items-center gap-1 text-[#C85A32] font-semibold group-hover:underline">
            <span>{pathname === "/pipeline" ? "Viewing Pipeline" : "Return to Pipeline"}</span>
            <ExternalLink className="w-3 h-3" />
          </div>
        </div>
      </div>
    </div>
  );
}

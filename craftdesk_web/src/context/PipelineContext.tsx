"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { GcsFolderItem } from "@/components/gcs/EnterpriseGcsThemeSelector";
import { useAuth } from "./AuthContext";

function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return "/api/v1";
}

export interface PipelineStageStatus {
  stage_name: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  progress_percent: number;
  images_done: number;
  images_total: number;
  elapsed_seconds: number | null;
  estimated_time_remaining_sec: number | null;
  error_message: string | null;
  stderr_log: string | null;
  live_log: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineJobItem {
  job_id: string;
  theme_slug: string;
  display_name: string;
  date_folder: string;
  gcs_prefix: string;
  status: "queued" | "running" | "completed" | "failed" | "paused" | "interrupted";
  current_stage: string | null;
  stages: PipelineStageStatus[];
  total_progress: number;
  elapsed_seconds: number;
  estimated_eta_sec: number | null;
  hero_image_url: string | null;
  mockups: string[];
  pdf_drive_link: string | null;
  pdf_local_path: string | null;
  error_msg: string | null;
}

interface PipelineContextType {
  // GCS Folders Session Cache
  gcsFolders: GcsFolderItem[];
  isLoadingGcs: boolean;
  fetchGcsFolders: (force?: boolean) => Promise<void>;

  // ComfyUI State
  comfyRunning: boolean;
  comfyPid: number | null;
  comfyStarting: boolean;
  checkComfyStatus: () => Promise<void>;
  startComfy: () => Promise<void>;

  // Batch Execution State
  batchQueue: PipelineJobItem[];
  activeJobIndex: number;
  isBatchRunning: boolean;
  isBatchPaused: boolean;
  activeJob: PipelineJobItem | null;

  // Actions
  startBatch: (folders: GcsFolderItem[]) => Promise<void>;
  pauseBatch: () => void;
  resumeBatch: () => void;
  cancelBatch: () => void;
  clearBatch: () => void;
  retryStage: (jobId: string, stageName: string) => Promise<void>;
  resumeJob: (jobId: string) => Promise<void>;

  // Notification bell (replaces floating widget)
  hasActiveNotification: boolean;
}

const INITIAL_STAGES: PipelineStageStatus[] = [
  { stage_name: "image_gen", label: "🎨 Stage 1: Image Generation (ComfyUI)", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
  { stage_name: "bg_removal", label: "✂️ Stage 2: Background Removal (rembg)", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
  { stage_name: "upscaling", label: "🔍 Stage 3: AI Upscaling (Real-ESRGAN / 4×)", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
  { stage_name: "mockup_creation", label: "🖼️ Stage 4: Mockup Creation", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
  { stage_name: "pdf_generation", label: "📄 Stage 5: Clickable PDF Wrap Generation", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
  { stage_name: "metadata_generation", label: "📝 Stage 6: Etsy Metadata (300 DPI & 13 Tags)", status: "pending", progress_percent: 0, images_done: 0, images_total: 0, elapsed_seconds: null, estimated_time_remaining_sec: null, error_message: null, stderr_log: null, live_log: null, started_at: null, completed_at: null },
];

const PipelineContext = createContext<PipelineContextType | undefined>(undefined);
const SESSION_CACHE_KEY = "craftdesk_gcs_folders_session_v1";

// ---------------------------------------------------------------------------
// Helper: Map a backend job response to frontend PipelineJobItem
// ---------------------------------------------------------------------------
function mapBackendJob(job: any): PipelineJobItem {
  const fetchedStages: PipelineStageStatus[] = job.stages || [];
  const compStages = fetchedStages.filter((s) => s.status === "completed").length;
  const runStage = fetchedStages.find((s) => s.status === "running");
  const runPct = runStage ? runStage.progress_percent : 0;
  const overallPct =
    fetchedStages.length > 0
      ? Math.min(100, Math.round(((compStages * 100 + runPct) / (fetchedStages.length * 100)) * 100))
      : 0;

  const activeStageWithEta = fetchedStages.find(
    (s) => s.status === "running" && s.estimated_time_remaining_sec != null
  );

  return {
    job_id: job.job_id,
    theme_slug: job.theme_name,
    display_name: job.theme_name,
    date_folder: job.created_at ? job.created_at.split("T")[0] : "",
    gcs_prefix: job.prompt_file_path || "",
    status: job.status as PipelineJobItem["status"],
    current_stage: job.current_stage,
    stages: fetchedStages,
    total_progress: overallPct,
    elapsed_seconds: fetchedStages.reduce((sum: number, s: any) => sum + (s.elapsed_seconds || 0), 0),
    estimated_eta_sec: activeStageWithEta ? activeStageWithEta.estimated_time_remaining_sec : null,
    hero_image_url: job.hero_image_url,
    mockups: job.mockups || [],
    pdf_drive_link: job.pdf_drive_link,
    pdf_local_path: job.pdf_local_path,
    error_msg: fetchedStages.find((s) => s.error_message)?.error_message || null,
  };
}

export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth();

  // GCS Folder Cache State
  const [gcsFolders, setGcsFolders] = useState<GcsFolderItem[]>([]);
  const [isLoadingGcs, setIsLoadingGcs] = useState(false);

  // ComfyUI State
  const [comfyRunning, setComfyRunning] = useState(false);
  const [comfyPid, setComfyPid] = useState<number | null>(null);
  const [comfyStarting, setComfyStarting] = useState(false);

  // Batch Execution State
  const [batchQueue, setBatchQueue] = useState<PipelineJobItem[]>([]);
  const [activeJobIndex, setActiveJobIndex] = useState<number>(-1);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [isBatchPaused, setIsBatchPaused] = useState(false);

  // Refs for stable access inside async callbacks
  const activeJobIndexRef = useRef(activeJobIndex);
  const isBatchRunningRef = useRef(isBatchRunning);
  const isBatchPausedRef = useRef(isBatchPaused);
  const batchQueueRef = useRef(batchQueue);
  const gcsFoldersRef = useRef(gcsFolders);

  // Sync suppression — prevents ghost re-fetches after cancel/clear
  const suppressSyncUntilRef = useRef<number>(0);

  activeJobIndexRef.current = activeJobIndex;
  isBatchRunningRef.current = isBatchRunning;
  isBatchPausedRef.current = isBatchPaused;
  batchQueueRef.current = batchQueue;
  gcsFoldersRef.current = gcsFolders;

  // ── GCS Folders ──────────────────────────────────────────────────────────

  // Restore from sessionStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const cached = sessionStorage.getItem(SESSION_CACHE_KEY);
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setGcsFolders(parsed);
          }
        }
      } catch {
        // Ignore
      }
    }
  }, []);

  const fetchGcsFolders = useCallback(async (force = false) => {
    if (!force && gcsFoldersRef.current.length > 0) return;
    setIsLoadingGcs(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
      const res = await fetch(`${getApiBaseUrl()}/etsy/gcs-folders`, {
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        const data = await res.json();
        const fetched = data.folders || [];
        setGcsFolders(fetched);
        if (typeof window !== "undefined" && fetched.length > 0) {
          sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(fetched));
        }
      }
    } catch {
      // Keep existing
    } finally {
      setIsLoadingGcs(false);
    }
  }, []);

  // ── ComfyUI ──────────────────────────────────────────────────────────────

  const checkComfyStatus = useCallback(async () => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
      const res = await fetch(`${getApiBaseUrl()}/pipeline/comfyui/status`, {
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        const data = await res.json();
        setComfyRunning(data.running);
        setComfyPid(data.pid ?? null);
      }
    } catch {
      // Ignore
    }
  }, []);

  const startComfy = useCallback(async () => {
    setComfyStarting(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
      const res = await fetch(`${getApiBaseUrl()}/pipeline/comfyui/start`, {
        method: "POST",
        headers: { Authorization: token ? `Bearer ${token}` : "" },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "started" || data.status === "already_running") {
          setComfyRunning(true);
        }
        setTimeout(checkComfyStatus, 3000);
      }
    } catch (err) {
      alert(`Could not start ComfyUI: ${err}`);
    } finally {
      setComfyStarting(false);
    }
  }, [checkComfyStatus]);

  useEffect(() => {
    checkComfyStatus();
  }, [checkComfyStatus]);

  // ── Backend Job Sync ─────────────────────────────────────────────────────

  const syncJobsFromBackend = useCallback(async () => {
    // Suppress sync for 10 seconds after cancel/clear to prevent ghost re-fetch
    if (Date.now() < suppressSyncUntilRef.current) {
      return;
    }

    const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
    if (!token) return;

    try {
      const res = await fetch(`${getApiBaseUrl()}/pipeline/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        console.warn("[PipelineContext] Token expired during job sync. Logging out.");
        logout();
        return;
      }

      if (!res.ok) return;

      const data = await res.json();
      if (!Array.isArray(data)) return;

      const mappedJobs: PipelineJobItem[] = data.map(mapBackendJob);

      setBatchQueue((prev) => {
        // If local queue is empty, restore from backend
        if (prev.length === 0) {
          // Only restore genuinely active jobs (running/queued/interrupted)
          // Do NOT restore completed/failed — they are purged from cache
          const activeJobs = mappedJobs.filter(
            (rj) => rj.status === "running" || rj.status === "queued" || rj.status === "interrupted"
          );

          const runningIdx = activeJobs.findIndex((j) => j.status === "running");
          if (runningIdx !== -1) {
            setActiveJobIndex(runningIdx);
          } else if (activeJobs.length > 0 && activeJobIndexRef.current === -1) {
            setActiveJobIndex(0);
          }
          return activeJobs;
        }

        // Merge: update existing local jobs with fresh backend data
        const merged = prev.map((localJob) => {
          const remoteJob = mappedJobs.find((rj) => rj.job_id === localJob.job_id);
          if (remoteJob) {
            return { ...localJob, ...remoteJob };
          }
          return localJob;
        });

        // Add genuinely new running jobs from backend (e.g. resumed from another device)
        mappedJobs.forEach((rj) => {
          if (!merged.some((lj) => lj.job_id === rj.job_id)) {
            if (rj.status === "running" || rj.status === "queued") {
              merged.push(rj);
            }
          }
        });

        const runningIdx = merged.findIndex((j) => j.status === "running");
        if (runningIdx !== -1 && activeJobIndexRef.current !== runningIdx) {
          setActiveJobIndex(runningIdx);
        }

        return merged;
      });
    } catch (err) {
      console.error("[PipelineContext] Failed to sync jobs:", err);
    }
  }, [logout]);

  // Adaptive polling: only poll when there are active jobs
  useEffect(() => {
    // Initial sync on mount
    syncJobsFromBackend();

    let timeoutId: NodeJS.Timeout;

    const runSyncLoop = () => {
      const hasActive = batchQueueRef.current.some(
        (j) => j.status === "running" || j.status === "queued"
      );
      const isLoopRunning = isBatchRunningRef.current;

      // If no active jobs and no batch loop running, DON'T poll at all
      if (!hasActive && !isLoopRunning) {
        return; // Stop the loop — it will be restarted by startBatch/resumeJob
      }

      // Active jobs exist → poll every 4 seconds
      const delay = 4000;

      timeoutId = setTimeout(async () => {
        await syncJobsFromBackend();
        runSyncLoop();
      }, delay);
    };

    runSyncLoop();

    return () => clearTimeout(timeoutId);
  }, [syncJobsFromBackend]);

  // Restart sync loop when batch starts running
  const restartSyncLoop = useCallback(() => {
    // Trigger a re-render which causes the useEffect above to re-run
    // by doing a harmless state update
    syncJobsFromBackend();
  }, [syncJobsFromBackend]);

  // ── Batch Queue Processing Loop ──────────────────────────────────────────

  const runNextJobInQueue = useCallback(async () => {
    const queue = batchQueueRef.current;
    const currentIndex = activeJobIndexRef.current;

    if (!isBatchRunningRef.current) return;
    const nextIndex = currentIndex + 1;
    if (nextIndex >= queue.length) {
      setIsBatchRunning(false);
      setActiveJobIndex(-1);
      return;
    }

    setActiveJobIndex(nextIndex);
    setBatchQueue((prev) =>
      prev.map((job, idx) => (idx === nextIndex ? { ...job, status: "running" } : job))
    );

    const targetJob = queue[nextIndex];
    const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;

    try {
      const startRes = await fetch(`${getApiBaseUrl()}/pipeline/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          prompt_file_path: targetJob.gcs_prefix,
          theme_name: targetJob.display_name,
        }),
      });

      if (!startRes.ok) {
        const errBody = await startRes.text();
        throw new Error(
          `Failed to start job for '${targetJob.display_name}': ${startRes.status} — ${errBody}`
        );
      }

      const startData = await startRes.json();
      const realJobId = startData.job_id;

      setBatchQueue((prev) =>
        prev.map((j, idx) => (idx === nextIndex ? { ...j, job_id: realJobId } : j))
      );

      let isDone = false;
      while (!isDone && isBatchRunningRef.current) {
        while (isBatchPausedRef.current && isBatchRunningRef.current) {
          await new Promise((r) => setTimeout(r, 1000));
        }

        if (!isBatchRunningRef.current) break;

        await new Promise((r) => setTimeout(r, 2000));
        if (!isBatchRunningRef.current) break;

        const pollRes = await fetch(`${getApiBaseUrl()}/pipeline/jobs/${realJobId}`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        });

        if (pollRes.ok) {
          const pollData = await pollRes.json();
          const fetchedStages: PipelineStageStatus[] = pollData.stages || [];
          const statusStr = pollData.status;

          const compStages = fetchedStages.filter((s) => s.status === "completed").length;
          const runStage = fetchedStages.find((s) => s.status === "running");
          const runPct = runStage ? runStage.progress_percent : 0;
          const overallPct = Math.min(
            100,
            Math.round(((compStages * 100 + runPct) / (fetchedStages.length * 100)) * 100)
          );

          const activeStageWithEta = fetchedStages.find(
            (s) => s.status === "running" && s.estimated_time_remaining_sec != null
          );
          const currentEta = activeStageWithEta ? activeStageWithEta.estimated_time_remaining_sec : null;

          setBatchQueue((prev) =>
            prev.map((j, idx) => {
              if (idx !== nextIndex) return j;
              return {
                ...j,
                status: statusStr === "completed" ? "completed" : statusStr === "failed" ? "failed" : "running",
                current_stage: pollData.current_stage || j.current_stage,
                stages: fetchedStages,
                total_progress: overallPct,
                estimated_eta_sec: currentEta,
                hero_image_url: pollData.hero_image_url || j.hero_image_url,
                mockups: pollData.mockups || j.mockups,
                pdf_drive_link: pollData.pdf_drive_link || j.pdf_drive_link,
                pdf_local_path: pollData.pdf_local_path || j.pdf_local_path,
              };
            })
          );

          if (statusStr === "completed" || statusStr === "failed") {
            isDone = true;
          }
        }
      }
    } catch (err: any) {
      setBatchQueue((prev) =>
        prev.map((j, idx) =>
          idx === nextIndex
            ? { ...j, status: "failed", error_msg: err?.message || "Execution error" }
            : j
        )
      );
    }

    if (isBatchRunningRef.current) {
      setTimeout(() => {
        runNextJobInQueue();
      }, 1000);
    }
  }, []);

  // ── Actions ──────────────────────────────────────────────────────────────

  const startBatch = useCallback(async (folders: GcsFolderItem[]) => {
    if (!folders.length) return;

    // FULL REPLACEMENT — old cancelled jobs cannot persist
    const newJobs: PipelineJobItem[] = folders.map((f, idx) => ({
      job_id: `pending-${idx}-${Date.now()}`,
      theme_slug: f.theme_slug,
      display_name: f.display_name,
      date_folder: f.date_folder,
      gcs_prefix: f.gcs_prefix,
      status: "queued",
      current_stage: null,
      stages: INITIAL_STAGES.map((s) => ({ ...s })),
      total_progress: 0,
      elapsed_seconds: 0,
      estimated_eta_sec: null,
      hero_image_url: null,
      mockups: [],
      pdf_drive_link: null,
      pdf_local_path: null,
      error_msg: null,
    }));

    // Clear any sync suppression from previous cancel
    suppressSyncUntilRef.current = 0;

    setBatchQueue(newJobs);
    setActiveJobIndex(-1);
    setIsBatchRunning(true);
    setIsBatchPaused(false);

    setTimeout(() => {
      runNextJobInQueue();
    }, 300);
  }, [runNextJobInQueue]);

  const pauseBatch = useCallback(() => {
    setIsBatchPaused(true);
    isBatchPausedRef.current = true;
    setBatchQueue((prev) =>
      prev.map((j, idx) => (idx === activeJobIndexRef.current ? { ...j, status: "paused" } : j))
    );
  }, []);

  const resumeBatch = useCallback(() => {
    setIsBatchPaused(false);
    isBatchPausedRef.current = false;
    setBatchQueue((prev) =>
      prev.map((j, idx) => (idx === activeJobIndexRef.current ? { ...j, status: "running" } : j))
    );
  }, []);

  const cancelBatch = useCallback(async () => {
    // 1. Stop the batch loop IMMEDIATELY
    setIsBatchRunning(false);
    setIsBatchPaused(false);
    isBatchRunningRef.current = false;
    isBatchPausedRef.current = false;

    // 2. Suppress sync for 10 seconds to prevent ghost re-fetch
    suppressSyncUntilRef.current = Date.now() + 10000;

    // 3. Stop the active backend job
    const active = activeJobIndexRef.current >= 0 ? batchQueueRef.current[activeJobIndexRef.current] : null;
    if (active && (active.status === "running" || active.status === "paused" || active.status === "queued")) {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
        await fetch(`${getApiBaseUrl()}/pipeline/jobs/${active.job_id}/stop`, {
          method: "POST",
          headers: { Authorization: token ? `Bearer ${token}` : "" },
        });
      } catch (err) {
        console.error("[PipelineContext] Failed to stop running job on backend:", err);
      }
    }

    // 4. Clear everything
    setActiveJobIndex(-1);
    activeJobIndexRef.current = -1;
    setBatchQueue([]);
    batchQueueRef.current = [];
  }, []);

  const clearBatch = useCallback(() => {
    setIsBatchRunning(false);
    setIsBatchPaused(false);
    isBatchRunningRef.current = false;
    isBatchPausedRef.current = false;

    // Suppress sync for 10 seconds to prevent ghost re-fetch
    suppressSyncUntilRef.current = Date.now() + 10000;

    setActiveJobIndex(-1);
    activeJobIndexRef.current = -1;
    setBatchQueue([]);
    batchQueueRef.current = [];
  }, []);

  const retryStage = useCallback(async (jobId: string, stageName: string) => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
      const res = await fetch(`${getApiBaseUrl()}/pipeline/jobs/${jobId}/stages/${stageName}/retry`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
      });
      if (!res.ok) {
        const errBody = await res.text();
        alert(`Retry failed: ${errBody}`);
      }
    } catch (err) {
      alert(`Error retrying stage: ${err}`);
    }
  }, []);

  const resumeJob = useCallback(async (jobId: string) => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("craftdesk_access_token") : null;
      const res = await fetch(`${getApiBaseUrl()}/pipeline/jobs/${jobId}/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
      });
      if (!res.ok) {
        const errBody = await res.text();
        alert(`Resume failed: ${errBody}`);
        return;
      }

      // Clear sync suppression and trigger immediate sync
      suppressSyncUntilRef.current = 0;
      await syncJobsFromBackend();
    } catch (err) {
      alert(`Error resuming job: ${err}`);
    }
  }, [syncJobsFromBackend]);

  // ── Derived State ────────────────────────────────────────────────────────

  const activeJob =
    activeJobIndex >= 0 && activeJobIndex < batchQueue.length
      ? batchQueue[activeJobIndex]
      : null;

  // Notification bell: only show for genuinely running jobs
  const hasActiveNotification = batchQueue.some(
    (j) => j.status === "running" || j.status === "paused"
  );

  return (
    <PipelineContext.Provider
      value={{
        gcsFolders,
        isLoadingGcs,
        fetchGcsFolders,
        comfyRunning,
        comfyPid,
        comfyStarting,
        checkComfyStatus,
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
        resumeJob,
        hasActiveNotification,
      }}
    >
      {children}
    </PipelineContext.Provider>
  );
}

export function usePipeline() {
  const context = useContext(PipelineContext);
  if (!context) {
    throw new Error("usePipeline must be used within a PipelineProvider");
  }
  return context;
}

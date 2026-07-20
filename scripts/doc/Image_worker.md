# Architecture Plan: Image Generation on GCP

> [!IMPORTANT]
> **Two storage routing decisions confirmed by user (2026-07-20) — to be implemented in Phase 2:**
> 1. Prompt `.txt` files → uploaded to **GCS** (not Google Drive)
> 2. After upscaling → images delivered to **Google Drive** (client delivery), then **raw + upscaled deleted from GCS** (only `no_bg/` kept in GCS for pipeline use)

**Date:** 2026-07-20  
**Status:** proposed — awaiting approval

---

## Problem Summary

The Colab notebook uses **z_image_turbo** (Lumina2-based diffusion model, ~25 GB) in ComfyUI for image generation, with a flat file-based state machine (`state.json` + lock files). This needs to move to GCP with proper job state tracking, cost visibility per stage, and a foundation for a future management UI.

---

## Your Questions — Answered

---

### Q1: Is Firestore a good fit? Is it scalable? What does it cost?

**What Firestore is:**
Firestore is Google Cloud's **managed, serverless NoSQL document database**. Documents are organized in collections (e.g., `jobs/{job_id}`). It is NOT a relational database — but that's perfectly fine here because our data is naturally document-shaped (one document = one job, with nested stage status).

**Is it scalable?**

| Property | Answer |
|---|---|
| Max documents per collection | Unlimited |
| Max concurrent connections | Millions |
| Auto-scaling | Yes — fully managed, no servers to manage |
| Real-time listeners | Yes — browser/UI gets live updates pushed, no polling |
| Multi-VM safe | Yes — atomic transactions replace your lock files |

For your use case (~10–100 jobs/day, 5 stages each), Firestore is **massively oversized** in the best way — you'll never hit a limit.

**What does it cost?**

The free tier is generous enough that you may **never pay for Firestore** at your scale:

| Operation | Free per day | Paid (beyond free) |
|---|---|---|
| Document reads | 50,000 | $0.03 per 100,000 |
| Document writes | 20,000 | $0.09 per 100,000 |
| Document deletes | 20,000 | $0.01 per 100,000 |
| Storage | 1 GiB | $0.18/GiB/month |

**Your estimated usage per day (100 jobs × 5 stages each):**
- Writes: ~500 state updates → well within 20,000 free
- Reads: ~1,000 polls → well within 50,000 free

**💰 Estimated Firestore cost: ~$0/month** at your scale. The free tier covers it.

---

### Q2: Google Drive vs GCS — Should we switch? What does GCS cost?

This is the most important cost question. Here's a direct comparison:

| Feature | Google Drive (current) | Google Cloud Storage (GCS) |
|---|---|---|
| Free storage | 15 GB | 5 GB (then paid) |
| Cost beyond free | Google One plans (~$3/month for 100 GB) | ~$0.02/GB/month (Standard) |
| Works with Service Accounts | ❌ Often hits quota/sharing issues | ✅ Native machine access |
| Upload reliability | ❌ You've already seen 404 errors | ✅ Production-grade, 99.99% uptime |
| Multi-VM file sharing | ❌ Sync delays, lock conflicts | ✅ Instant, atomic |
| Download signed URLs (for customers) | Complex sharing links | Simple signed URLs with expiry |
| Region co-located with VM | ❌ No | ✅ Yes → **free intra-region transfer** |

**GCS Cost Estimate for your pipeline:**

Assume per job: 170 raw images (~5 MB each) = ~850 MB raw + 850 MB upscaled + 200 MB mockups ≈ ~2 GB per job.

| Item | Size | Cost |
|---|---|---|
| Storage (50 jobs × 2 GB) | 100 GB | ~$2/month |
| VM → GCS upload (intra-region) | Any amount | **$0 (free!)** |
| GCS → UI download | ~10 GB/month | ~$1.20/month |

**💰 Estimated GCS cost: ~$3–4/month** for 50 jobs/month.

**Recommendation:** ✅ Use GCS for all pipeline artifacts (raw, no_bg, upscaled, mockups). Use Google Drive only for final customer delivery ZIPs (manual sharing, same as now).

---

### Q3: VM Disk Size

Updated to **70 GB SSD** as requested. Breakdown:
- OS + ComfyUI + Python: ~15 GB
- Models (25 GB): ae.safetensors + qwen_3_4b + z_image_turbo_bf16
- Working temp space: ~20 GB (in-progress generation)
- Buffer: ~10 GB

---

## Model Confirmed: z_image_turbo (Lumina2 / AuraFlow architecture)

From your workflow file `image_z_image_turbo1.json`:

| Node | Role |
|---|---|
| `CLIPLoader` (qwen_3_4b.safetensors, lumina2) | Text encoder |
| `VAELoader` (ae.safetensors) | VAE decoder |
| `UNETLoader` (z_image_turbo_bf16.safetensors) | Diffusion model |
| `ModelSamplingAuraFlow` (shift=3) | Sampling schedule |
| `KSampler` (steps=8, cfg=1, res_multistep) | Sampling — 8 steps, very fast |
| `EmptySD3LatentImage` (1024×1024, batch=1) | Output resolution |
| `CLIPTextEncode` | **← This is where we inject your prompt** |
| `SaveImage` (prefix: z-image-turbo) | Output file |

The `CLIPTextEncode` node `57:27` → `text` field is the **injection point** for our `image_worker.py`. We'll swap the text value per prompt before submitting to ComfyUI.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                            GCP Project                              │
│                                                                    │
│  ┌────────────────┐   ┌─────────────────────────────────────────┐ │
│  │  Prompt VM     │   │     Image Generation GPU VM             │ │
│  │ (n1-std-2,     │   │ (n1-standard-8 + NVIDIA T4 GPU)         │ │
│  │  no GPU)       │   │  Disk: 70 GB SSD                        │ │
│  │                │   │                                         │ │
│  │ run_prompts.py │   │  ┌────────────────────────────────────┐ │ │
│  │   ↓            │   │  │  ComfyUI Server (port 8188)        │ │ │
│  │ Writes prompts │   │  │  z_image_turbo_bf16.safetensors    │ │ │
│  │ to Firestore   │   │  │  qwen_3_4b.safetensors             │ │ │
│  │                │   │  │  ae.safetensors                    │ │ │
│  └────────┬───────┘   │  └───────────────┬────────────────────┘ │ │
│           │           │                  │ HTTP API (localhost)   │ │
│           ▼           │  ┌───────────────▼────────────────────┐ │ │
│  ┌────────────────┐   │  │  image_worker.py (systemd service) │ │ │
│  │  Cloud         │   │  │  - Poll Firestore for PENDING jobs │ │ │
│  │  Firestore     │◄──┤  │  - Inject prompt → workflow JSON   │ │ │
│  │                │   │  │  - POST to ComfyUI /prompt API     │ │ │
│  │  jobs/         │   │  │  - Poll /history for completion    │ │ │
│  │   {job_id}/    │   │  │  - Upload PNG to GCS               │ │ │
│  │    stages/     │───►  │  - Update Firestore progress/cost  │ │ │
│  │     image_gen/ │   │  └────────────────────────────────────┘ │ │
│  │      status    │   └─────────────────────────────────────────┘ │
│  │      cost_usd  │                                               │
│  │      imgs_done │   ┌─────────────────────────────────────────┐ │
│  └────────────────┘   │  Cloud Storage (GCS Bucket)             │ │
│                        │  gs://etsy-pipeline/                    │ │
│                        │    prompts/{date}/{theme}.txt           │ │
│                        │    raw_images/{date}/{theme}/*.png      │ │
│                        │    no_bg/{date}/{theme}/*.png           │ │
│                        │    upscaled/{date}/{theme}/*.png        │ │
│                        │    mockups/{date}/{theme}/*.jpg         │ │
│                        └─────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## Per-Stage Cost Tracking (UI Comment Addressed)

Every stage will record its cost in Firestore so the UI can show live cost at each step:

```
jobs/{job_id}/stages/prompt_generation/
  status: COMPLETED
  cost_usd: 0.021          ← Gemini input/output token cost
  input_tokens: 1200
  output_tokens: 8500

jobs/{job_id}/stages/image_generation/
  status: RUNNING
  cost_usd: 1.47           ← GPU VM compute cost (hourly rate × time used)
  images_total: 170
  images_done: 45
  gpu_hours: 1.96
  gpu_rate_usd_per_hr: 0.75

jobs/{job_id}/stages/bg_removal/
  cost_usd: 0.12           ← API call cost (if using external API) or GPU time

jobs/{job_id}/stages/upscaling/
  cost_usd: 0.18           ← GPU time cost

jobs/{job_id}/stages/mockup/
  cost_usd: 0.05           ← CPU time cost
```

**Dashboard will show:**
```
Job: "Lilo & Stitch" (birthday)
✅ Prompt Generation   — Done    | Cost: $0.021
🔄 Image Generation   — Running  | Cost: $1.47 so far | 45/170 images done
⏳ BG Removal         — Waiting  | Cost: —
⏳ Upscaling          — Waiting  | Cost: —
⏳ Mockup             — Waiting  | Cost: —
─────────────────────────────────────────────────
Total so far:  $1.49
```

---

## Full Cost Summary Per Job

| Component | Cost Estimate | Notes |
|---|---|---|
| Gemini Prompts (Vertex AI) | ~$0.02–0.05 per job | ~170 prompts, 2.5 Flash pricing |
| GPU VM — Image Generation | ~$0.75/hr × ~2 hrs = **$1.50** | 170 images × 8 steps at ~2-3 min/image on T4 → ~6 hrs? TBD |
| GCS Storage | ~$0.04/job | ~2 GB per job × $0.02/GB |
| Firestore | ~$0 | Free tier covers all ops |
| **Total per job** | **~$1.60–3.00** | GPU cost dominates |

> [!TIP]
> **GPU Spot VMs** can reduce GPU cost by 60-70% → ~$0.22/hr instead of $0.75/hr. The VM can be interrupted but ComfyUI can resume from the last prompt checkpoint. Strongly recommended for batch workloads.

> [!IMPORTANT]
> **VM only runs when generating images.** You start it before a batch and stop it when done. If you generate for 4 hours/day, you pay ~$3/day GPU, not 24/7.

---

## Implementation Phases

### Phase 1 — Firestore + image_worker skeleton (no GPU VM cost yet)
- [ ] Add `google-cloud-firestore` and `google-cloud-storage` to `pyproject.toml`
- [ ] Create `etsy_pipeline/services/firestore_store.py` — Firestore job state service
- [ ] Create `etsy_pipeline/workers/image_worker.py` — with ComfyUI API caller using your workflow JSON
- [ ] Update `Job` model to write state to Firestore (in addition to in-memory)
- [ ] Add `cost_usd` and `images_done` / `images_total` fields to `StageResult`

### Phase 2 — GCS Integration
- [ ] Create `etsy_pipeline/services/gcs_store.py` — GCS upload/download service
- [ ] Update `run_prompts.py` to also upload prompt `.txt` to GCS
- [ ] `image_worker.py` downloads prompt from GCS, uploads images to GCS

### Phase 3 — GPU VM Setup
- [ ] Create GCP GPU VM (n1-standard-8 + T4, 70 GB SSD)
- [ ] Startup script: installs ComfyUI, downloads models from HuggingFace
- [ ] Deploy `image_worker.py` as a `systemd` service
- [ ] End-to-end test: prompt → Firestore → image_worker → ComfyUI → GCS

### Phase 4 — BG Removal, Upscaling, Mockup (same pattern)
### Phase 5 — UI Dashboard (FastAPI + real-time Firestore listener)

---

## Future Storage Routing Decisions (Confirmed)

These two decisions are **locked in** and will be implemented in Phase 2 (GCS Integration).

---

### Decision 1: Prompt File Upload → GCS (not Google Drive)

**Current behaviour** (`run_prompts.py` lines 154–162):  
After generating prompts, the `.txt` file is saved locally and then uploaded to Google Drive via `GoogleDriveService.upload_file()`.

**New behaviour:**  
Upload the prompt `.txt` to **GCS** under the path:
```
gs://etsy-pipeline/prompts/{date}/{theme_slug}.txt
```
Google Drive upload for prompts will be **removed entirely** from `run_prompts.py`.

**Files to change:**

| File | Change |
|---|---|
| `scripts/run_prompts.py` | Replace `GoogleDriveService` call with `GCSStore.upload_file(prompts_path, gcs_path)` |
| `etsy_pipeline/services/gcs_store.py` | New service — Phase 2 |
| `etsy_pipeline/config/settings.py` | Add `GCS_BUCKET_NAME` setting |
| `.env` / `.env.example` | Add `GCS_BUCKET_NAME=etsy-pipeline` |

**Why:** The `image_worker.py` on the GPU VM needs to read the prompt file from a machine-accessible path. GCS is native machine access — no OAuth dance, no 404s like Drive.

---

### Decision 2: Post-Upscale Delivery → Drive + GCS Cleanup

**Flow after upscaling completes:**

```
Upscaling COMPLETED
        │
        ▼
┌─────────────────────────────────────────┐
│ 1. Upload upscaled images to Google     │
│    Drive (client delivery folder)       │
│    Drive path: {client_folder}/{theme}/ │
│                                         │
│ 2. Delete from GCS:                     │
│    ✗ raw_images/{date}/{theme}/         │
│    ✗ upscaled/{date}/{theme}/           │
│                                         │
│ 3. KEEP in GCS (pipeline still needs):  │
│    ✓ no_bg/{date}/{theme}/  ← mockup   │
│      stage reads from here              │
└─────────────────────────────────────────┘
        │
        ▼
  Mockup stage runs using no_bg/ images
        │
        ▼
  Mockup COMPLETED → upload to Drive
  → Delete no_bg/ from GCS
```

**GCS storage lifecycle per job:**

| Stage | GCS paths active | GCS paths deleted |
|---|---|---|
| After Image Gen | `raw_images/` | — |
| After BG Removal | `raw_images/`, `no_bg/` | `raw_images/` ✗ |
| After Upscaling | `no_bg/`, `upscaled/` | `upscaled/` ✗ → sent to Drive |
| After Mockup | `no_bg/` | `no_bg/` ✗ |
| **Final state** | **Nothing in GCS** | **All on Drive** |

**Net result:** GCS is used as **transient working storage only** — no long-term accumulation. Final customer assets always land on Google Drive.

**Files to change:**

| File | Change |
|---|---|
| `etsy_pipeline/workers/upscale_worker.py` | After completion: upload to Drive, delete `raw_images/` + `upscaled/` from GCS |
| `etsy_pipeline/workers/bg_removal_worker.py` | After completion: delete `raw_images/` from GCS |
| `etsy_pipeline/workers/mockup_worker.py` | After completion: upload mockups to Drive, delete `no_bg/` from GCS |
| `etsy_pipeline/services/gcs_store.py` | Add `delete_prefix(bucket, prefix)` method |
| `etsy_pipeline/services/google_drive.py` | Already exists — add `upload_folder(local_dir, drive_folder_id)` batch method |

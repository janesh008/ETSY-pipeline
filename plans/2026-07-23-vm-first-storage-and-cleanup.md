# Implementation Plan — VM-First Local File Management with Automated Cleanup & Multi-Cloud Delivery

Optimize pipeline file management by utilizing local VM disk space as a transient working directory, enforcing aggressive post-stage storage cleanup, saving upscaled images directly to Google Drive, backing up `no_bg` assets to both GCS and Drive, providing 3-tier fallbacks (VM -> GCS -> Drive) for metadata & Etsy upload stages, and vanishing all local VM theme folders once Etsy listing completes.

---

## 1. Architectural Flow Diagram

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                    VM-First Local File & Cleanup Strategy                                               |
+-------------------------------------------------------------------------------------------------------------------------+
  Stage 1: Image Generation   ---> 1. Save raw PNGs to VM disk (output/<date>/<slug>/raw_data/)
                                   2. Upload raw PNGs to GCS (Clipart/<date>/<slug>/raw_data/)
                                          │
                                          ▼
  Stage 2: BG Removal        ---> 1. Check local VM disk (raw_data/) [Fallback: GCS]
                                   2. Output: Save no_bg/ to VM disk (output/<date>/<slug>/no_bg/)
                                   3. Sync: Upload no_bg/ to BOTH:
                                      - GCS: Clipart/<date>/<slug>/no_bg/
                                      - Drive: Clipart/raw_data/<date>/<slug>/no_bg/
                                   4. CLEANUP: Delete raw_data/ from BOTH local VM disk & GCS
                                          │
                                          ├─────────────────────────────────────────┐
                                          ▼                                         ▼
  Stage 3: Upscaling         ---> 1. Check local VM disk (no_bg/)    Stage 4: Mockups & PDF  ---> 1. Check local VM disk (no_bg/)
                                   2. Fallback: Download from GCS/Drive                        2. Fallback: Download from GCS/Drive
                                   3. Output: Stream/push upscaled                             3. Output: Generate Mockups & PDF locally
                                      images DIRECTLY to Google Drive                          - Mockups: output/<date>/<slug>/mockups/
                                      (Clipart/main_data/<date>/<slug>/)                       - PDF: output/<date>/<slug>/pdf/
                                   4. NO local VM retention of upscaled                       4. Sync: Upload BOTH Mockups & PDF
                                      images                                                      to BOTH GCS & Google Drive
                                                                                                  - GCS: Clipart/<date>/<slug>/mockups/ & pdf/
                                                                                                  - Drive: Clipart/raw_data/<date>/<slug>/
                                                                                                           (mockups + PDF)
                                                                                                    │
                                                                                                    ▼
                                                                     Stage 5: Metadata & CSV ---> 1. Input: Check local VM disk
                                                                                                     (output/<date>/<slug>/mockups/)
                                                                                                     Fallback: Download GCS -> Drive
                                                                                                  2. Output: Save CSV to local VM disk
                                                                                                     (output/<date>/all_listings.csv)
                                                                                                  3. Sync: Upload CSV to BOTH GCS & Drive
                                                                                                    │
                                                                                                    ▼
                                                                     Stage 6: Etsy Upload    ---> 1. Input: Mockups from VM
                                                                      & Final VM Cleanup             (output/<date>/<slug>/mockups/)
                                                                                                     Fallback: GCS -> Drive
                                                                                                     CSV from VM (output/<date>/all_listings.csv)
                                                                                                     Fallback: GCS -> Drive
                                                                                                  2. Create draft & publish listing on Etsy
                                                                                                  3. Update & re-sync CSV (GCS & Drive)
                                                                                                  4. FINAL CLEANUP: Remove local VM theme folder
                                                                                                     (output/<date>/<slug>/) completely
```

---

## 2. Updated Refined Rules per Stage

1. **Stage 1 — Image Generation:**
   - Save raw PNGs to local VM disk: `output/<date>/<theme_slug>/raw_data/`.
   - Sync raw PNGs to GCS: `Clipart/<date>/<theme_slug>/raw_data/`.

2. **Stage 2 — BG Removal & Post-Stage Raw Cleanup:**
   - **Inputs:** Check local VM disk (`output/<date>/<theme_slug>/raw_data/`). If missing, fallback to downloading from GCS (`Clipart/<date>/<theme_slug>/raw_data/`).
   - **Outputs:** Save `no_bg/` images to local VM disk (`output/<date>/<theme_slug>/no_bg/`).
   - **Cloud Sync:** Upload `no_bg/` images to **BOTH GCS and Google Drive**:
     - **GCS:** `Clipart/<date>/<theme_slug>/no_bg/`
     - **Google Drive:** `Clipart/raw_data/<date>/<theme_slug>/no_bg/`
   - **POST-STAGE CLEANUP:** Upon successful completion of background removal, **delete `raw_data/` completely** from both local VM disk and GCS.

3. **Stage 3 — Upscaling (Direct-to-Drive):**
   - **Inputs:** Check local VM disk (`output/<date>/<theme_slug>/no_bg/`). If missing, fallback to GCS or Google Drive.
   - **Outputs:** Upscale images and push them **DIRECTLY to Google Drive** (`Clipart/main_data/<date>/<theme_slug>/`).
   - **Local Storage Policy:** Upscaled images are NOT retained on local VM disk to conserve disk space.

4. **Stage 4 — Mockups & PDF:**
   - **Inputs:** Uses **ONLY `no_bg/`** images (Check local VM disk `output/<date>/<theme_slug>/no_bg/`, fallback to GCS or Drive).
   - **Outputs:** Generate mockups and PDF in local theme subfolder:
     - Mockup PNGs: `output/<date>/<theme_slug>/mockups/`
     - PDF file: `output/<date>/<theme_slug>/pdf/` (or `output/<date>/<theme_slug>/<theme_slug>.pdf`)
   - **Cloud Sync:** Upload **BOTH Mockups and PDF** to **BOTH GCS and Google Drive**:
     - **GCS:** `Clipart/<date>/<theme_slug>/mockups/` & `Clipart/<date>/<theme_slug>/pdf/`
     - **Google Drive:** `Clipart/raw_data/<date>/<theme_slug>/` (Upload mockup PNGs & PDF file).

5. **Stage 5 — Metadata & CSV:**
   - **Inputs:** Check local VM theme mockups folder (`output/<date>/<theme_slug>/mockups/`). If missing, fallback to **GCS** (`Clipart/<date>/<theme_slug>/mockups/`) or **Google Drive** (`Clipart/raw_data/<date>/<theme_slug>/`).
   - **Outputs:** Save consolidated CSV (`all_listings.csv`) locally on VM disk at `output/<date>/all_listings.csv`.
   - **Cloud Sync:** Upload CSV to **BOTH GCS** (`csv/<date>/all_listings.csv`) and **Google Drive** (`Clipart/csv/<date>/all_listings.csv`).

6. **Stage 6 — Etsy Upload & Complete VM Cleanup:**
   - **Inputs:** 
     - **Mockups:** Check local VM theme mockups folder (`output/<date>/<theme_slug>/mockups/`). If missing, fallback to **GCS** (`Clipart/<date>/<theme_slug>/mockups/`) or **Google Drive** (`Clipart/raw_data/<date>/<theme_slug>/`).
     - **CSV:** Check local VM date folder (`output/<date>/all_listings.csv`). If missing, fallback to **GCS** (`csv/<date>/all_listings.csv`) or **Google Drive** (`Clipart/csv/<date>/all_listings.csv`).
   - **Execution:** Create draft listing, upload mockup images (Hero first), and activate listing via Etsy v3 API. Update consolidated CSV with Listing ID and URL, then re-sync CSV to GCS & Drive.
   - **FINAL PIPELINE CLEANUP:** Upon successful completion of Etsy upload, **completely delete/vanish the local VM theme folder** (`output/<date>/<theme_slug>/`) to leave zero residual clutter on the VM.

---

## 3. Detailed Input/Output & Cleanup Matrix

| Stage | Input Check Order | Local VM Working Path | Cloud Destination | Post-Stage Cleanup |
| :--- | :--- | :--- | :--- | :--- |
| **1. Image Gen** | Prompts from Job | `output/<date>/<slug>/raw_data/` | **GCS:** `Clipart/<date>/<slug>/raw_data/` | None |
| **2. BG Removal** | 1. VM: `output/<date>/<slug>/raw_data/`<br>2. GCS fallback | `output/<date>/<slug>/no_bg/` | **GCS:** `Clipart/<date>/<slug>/no_bg/`<br>**Drive:** `Clipart/raw_data/<date>/<slug>/no_bg/` | **Delete `raw_data/`** from VM & GCS |
| **3. Upscaling** | 1. VM: `output/<date>/<slug>/no_bg/`<br>2. GCS/Drive fallback | *None (Stream/Direct)* | **Drive ONLY:** `Clipart/main_data/<date>/<slug>/` | No local upscaled images retained |
| **4. Mockup & PDF**| 1. VM: `output/<date>/<slug>/no_bg/`<br>2. GCS/Drive fallback | `output/<date>/<slug>/mockups/` & `pdf/` | **GCS:** `mockups/` & `pdf/`<br>**Drive:** `Clipart/raw_data/<date>/<slug>/` (Mockups + PDF) | None |
| **5. Metadata & CSV**| 1. VM: `output/<date>/<slug>/mockups/`<br>2. GCS fallback<br>3. Drive fallback | `output/<date>/all_listings.csv` | **GCS:** `csv/<date>/all_listings.csv`<br>**Drive:** `Clipart/csv/<date>/all_listings.csv` | None |
| **6. Etsy Upload** | 1. VM: `output/<date>/<slug>/mockups/` & `output/<date>/all_listings.csv`<br>2. GCS fallback<br>3. Drive fallback | `output/<date>/<slug>/` | Etsy API v3 Draft & Active Listing | **Delete entire VM theme folder** (`output/<date>/<slug>/`) |

---

## 4. Proposed Code Modifications

### Common Helper Enhancement

#### [MODIFY] [storage_helper.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/storage_helper.py)
Extend `ensure_local_assets()` to support exact theme subfolder resolution with 3-tier fallback:
```python
def ensure_local_assets(
    local_dir: Path,
    gcs_prefix: str | None = None,
    drive_path_parts: list[str] | None = None,
    settings: Settings | None = None,
    file_patterns: list[str] | None = None,
) -> list[Path]:
    """1. Check local VM theme directory (e.g. output/<date>/<slug>/mockups/) for files.
       2. If empty, attempt download from GCS prefix.
       3. If still empty, attempt download from Google Drive path.
       4. Return list of resolved local file paths.
    """
```

### Worker Modules

#### [MODIFY] [metadata_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/metadata_worker.py)
- Use `ensure_local_assets()` for mockups input: 1. Local VM `output/<date>/<theme_slug>/mockups/` $\rightarrow$ 2. GCS `Clipart/<date>/<theme_slug>/mockups/` $\rightarrow$ 3. Google Drive `Clipart/raw_data/<date>/<theme_slug>/`.

#### [MODIFY] [etsy_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/etsy_worker.py) / [run_etsy_upload.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/run_etsy_upload.py)
- Use `ensure_local_assets()` for mockups images at `output/<date>/<theme_slug>/mockups/` before uploading to Etsy.
- Use `ensure_local_assets()` for `all_listings.csv` at `output/<date>/all_listings.csv` before updating listing ID and URL.
- Execute final VM cleanup: remove `output/<date>/<theme_slug>/` using `shutil.rmtree()`.

---

## 5. Verification Plan

### Automated Tests
- Run `pytest` on worker test suites.
- Add unit tests verifying `ensure_local_assets()` 3-tier fallback logic (VM -> GCS -> Drive).

### Manual Verification
- Run metadata worker and Etsy upload on job `cd77c921596b`.
- Confirm 3-tier fallback works when files are missing locally.
- Confirm local VM theme directory vanishes after Etsy upload completes.

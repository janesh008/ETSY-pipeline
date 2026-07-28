# CraftDesk Web Frontend — Detailed Page & Business Workflow Reference

This specification details the **Seller Business Intent**, **Component State Machine**, and **User Interaction Logic** for all 11 routes in `craftdesk_web`.

---

## 📄 1. Authentication Pages (`/login` & `/register`)

### `/login` — Seller Authentication
- **Business Intent:** Validates seller credentials and restores workspace session.
- **Business Logic Algorithm:**
  1. Captures `email` and `password`.
  2. Calls `api.login()`.
  3. Saves `access_token` and `refresh_token` to `localStorage`.
  4. Stores user profile in `localStorage` under `craftdesk_user`.
  5. Redirects to `/dashboard`.
- **Error Handling:** Displays red alert banner if credentials are invalid or server is unreachable.

### `/register` — Studio Registration
- **Business Intent:** Creates a new CraftDesk account and automatically logs the seller in upon success.
- **Business Logic Algorithm:**
  1. Captures `full_name`, `email`, and `password` (min 8 chars).
  2. Calls `api.register()`.
  3. Auto-triggers `login()` to fetch JWT tokens and navigate to `/dashboard`.

---

## 📄 2. Studio Workspace Dashboard (`/dashboard`)

- **Business Intent:** Provides high-level operational visibility over AI generation metrics and GCP GPU VM infrastructure.
- **Metrics Displayed:**
  - `Prompts Generated`: Total clipart prompts synthesized across batches.
  - `Pipelines Completed`: Number of 6-stage listing packages produced.
  - `Connected Shops`: Active Etsy store connections.
  - `GCP GPU VM Status Widget`: Displays GPU VM status (`Stopped 🔴` / `Booting ComfyUI... ⚙️` / `Ready ✅ (:8188)`) with Start/Stop controls.
- **Quick Handoff Cards:** Direct action buttons launching `/prompt-studio`, `/pipeline`, and `/shops`.

---

## 📄 3. AI Prompt Studio (`/prompt-studio`)

- **Business Intent:** Multi-modal prompt matrix generation for commercial watercolor clipart bundles.
- **User Workflow:**
  1. **Input Theme Text:** Enter subject e.g. "Wonder Woman Birthday Watercolor".
  2. **Etsy URL Scraper:** Paste competitor product link and click **"Scrape"**. System fetches title, description snippet, and thumbnail gallery to supply style inspiration.
  3. **Reference Images:** Drag & drop reference PNGs for Gemini 2.5 Vision style transfer.
  4. **Quantity Slider:** Adjust target prompt count between 5 and 50 (default 22).
  5. **Click "Generate AI Prompt Matrix":** Gemini 2.5 Flash synthesizes numbered clipart prompts.
  6. **Export Actions:**
     - Click **"Export to .txt"**: Generates and downloads plain text file.
     - Click **"Run 6-Stage Pipeline"**: Hands off prompt set to `/pipeline`.

---

## 📄 4. Etsy Shop Connector (`/shops`)

- **Business Intent:** Connect Etsy shops using PKCE OAuth 2.0 without exposing client secrets.
- **User Workflow:**
  1. Seller clicks **"Connect Etsy Shop"**.
  2. Frontend calls `/api/v1/etsy/auth/url` to retrieve `auth_url` and `code_verifier`.
  3. `code_verifier` is stored in `sessionStorage`.
  4. User is redirected to official Etsy consent screen.
  5. Upon approval, Etsy redirects back to callback URL.
  6. Frontend exchanges code for tokens (`/api/v1/etsy/auth/callback`). Tokens are encrypted via AES-256 Fernet and stored in PostgreSQL `etsy_shops`.
  7. Connected shop card appears with active status badge and Disconnect action.

---

## 📄 5. 6-Stage Pipeline Runner (`/pipeline`)

- **Left Panel Prompt Browser (Date-Wise Collapsible Folder Tree):**
  - **Date Accordions:** Displays saved prompt files grouped by date (e.g. `📁 2026-07-28`, `📁 2026-07-22`) with expand/collapse arrows (`ChevronDown`/`ChevronRight`) and total theme badges.
  - **Theme Cards:** Indented file cards under each date folder displaying theme name, prompt count, local/GCS status badge, and prompt preview snippet.
  - **Single-Click Selection:** Clicking a theme card selects it and prepares the pipeline runner.
- **Control Actions:**
  - **Run Pipeline Button:** Initiates execution for the selected prompt file.
  - **Stop Execution Button:** Red cancel button available during active execution to halt the running job gracefully (`POST /pipeline/jobs/{job_id}/stop`).
- **4 Visual States per Stage:**
  - `⏳ Pending`: Stage waiting in queue.
  - `⚡ Running`: Animated progress bar + percentage (0% → 50% → 100%).
  - `✅ Completed`: Green checkmark badge with completion timestamp. Supports 100% module checkpoint skipping when assets exist in GCS (`gs://bucket/Clipart/...`) or local storage.
  - `❌ Failed`: Crimson error card displaying root exception traceback, timestamp, **"View Stderr Log"** panel, and **"Retry Stage"** button.
- **Retry Logic:** Clicking **"Retry Stage"** resets only that failed stage to `running`, preserving all previously completed stage outputs.

---

## 📄 6. Gallery Review & Etsy Publisher (`/review/[job_id]`)

- **Business Intent:** Visual inspection, metadata editing, and 1-click publishing of Etsy draft listings.
- **Left Panel (Asset Inspection):**
  - Hero image card (`Hero.png`).
  - **Full Gallery Grid:** Displays ALL 4 mockups (T-Shirt, Mug, Frame, Tote Bag). Clicking any mockup opens a high-resolution **Lightbox Modal**.
  - Clickable PDF Wrap download link (Google Drive file).
- **Right Panel (Inline Metadata Editor):**
  - Listing Title input (140 max char counter).
  - Listing Description textarea.
  - 13 Etsy Tags manager (add/remove tag chips).
- **One-Click Etsy Publishing:**
  - Select connected shop from dropdown and click **"Push Draft Listing to Etsy Shop"**.
  - Calls `/api/v1/review/{job_id}/push-to-etsy`.
  - Displays instant success modal with direct link to view the draft listing on Etsy!

---

## 📄 7. Studio Settings & Key Store (`/settings`)

- **Business Intent:** Secure key store and profile management.
- **Sections:**
  1. Profile Settings: Update full name.
  2. GCP Compute Engine GPU VM Config: Set project ID, zone, instance name, and paste service account JSON key (AES-256 encrypted).
  3. AI Provider Keys: Store Gemini 2.5 Flash and Replicate API keys (AES-256 encrypted).

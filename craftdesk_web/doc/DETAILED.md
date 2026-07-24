# CraftDesk Web Frontend — Detailed Specification & Component Reference

## 📁 File Structure Map

```
craftdesk_web/
├── src/
│   ├── app/
│   │   ├── globals.css              # Design tokens (#F7F6F0 palette) & scrollbars
│   │   ├── layout.tsx               # Root layout (Outfit/Inter/Mono fonts & AuthProvider)
│   │   ├── page.tsx                 # Root redirect landing page
│   │   ├── login/
│   │   │   └── page.tsx             # Atelier Login UI
│   │   ├── register/
│   │   │   └── page.tsx             # Atelier Account Register UI
│   │   ├── dashboard/
│   │   │   └── page.tsx             # Studio Dashboard & GPU VM Status Widget
│   │   ├── prompt-studio/
│   │   │   └── page.tsx             # Multi-Input Prompt Studio & .txt Exporter
│   │   ├── shops/
│   │   │   └── page.tsx             # Etsy OAuth PKCE Shop Connector
│   │   ├── pipeline/
│   │   │   └── page.tsx             # 6-Stage Pipeline Runner & Failure Retry Card
│   │   ├── review/
│   │   │   └── [job_id]/
│   │   │       └── page.tsx         # Mockup Gallery Review, Lightbox & Etsy Publisher
│   │   └── settings/
│   │       └── page.tsx             # Studio Settings & AES-256 Key Store
│   ├── context/
│   │   └── AuthContext.tsx          # JWT local storage session & auth context
│   └── lib/
│       └── api.ts                   # Type-safe API fetch client
├── public/                          # Static branding & favicon assets
├── next.config.ts                   # Next.js configuration
├── package.json                     # Dependencies (next 16, react 19, lucide-react)
└── tsconfig.json                    # TypeScript path aliases (@/*)
```

---

## 🔍 Page Component Specification

### 1. `src/app/login/page.tsx`
- **Purpose:** User authentication interface.
- **State:** `email`, `password`, `error`, `isSubmitting`.
- **Flow:** Submits `login({ email, password })` to `AuthContext`, stores access/refresh tokens in `localStorage`, and redirects to `/dashboard`.

### 2. `src/app/dashboard/page.tsx`
- **Purpose:** Workspace overview.
- **Widgets:**
  - Stat 1: Prompts Generated (142)
  - Stat 2: Pipelines Completed (18)
  - Stat 3: Connected Etsy Shops (1)
  - Stat 4: GCP GPU VM Widget (`Stopped 🔴` → `Booting ComfyUI... ⚙️` → `Ready ✅ (:8188)`) with Start/Stop controls.
- **Quick Links:** Navigation cards to `/prompt-studio`, `/pipeline`, `/shops`.

### 3. `src/app/prompt-studio/page.tsx`
- **Purpose:** Multi-input AI prompt matrix generator.
- **Inputs:**
  1. Theme Text input (`Wonder Woman Birthday Watercolor`)
  2. Etsy URL auto-scraper with live preview (fetches title, description, thumbnails)
  3. Reference Image drag & drop uploader
  4. Target Prompt Count slider (5–50 prompts)
- **Outputs:**
  - `JetBrains Mono` sectioned prompt matrix viewer
  - One-click **"Export to .txt"** download button
  - "Run 6-Stage Pipeline" handoff button.

### 4. `src/app/shops/page.tsx`
- **Purpose:** Connected Etsy store manager.
- **Features:**
  - Multi-tenant S256 PKCE authorization trigger (`/etsy/auth/url`)
  - AES-256 Fernet security indicator banner
  - Connected shop list displaying shop ID, shop name, active token badge, and Disconnect button.

### 5. `src/app/pipeline/page.tsx`
- **Purpose:** 6-Stage pipeline execution & failure debugging.
- **Stages:** Image Gen → BG Removal → 4x Upscaling → Mockup Creation → PDF Wrap → 300 DPI Metadata.
- **Failure UI:** Displays root exception traceback, timestamp, **"View Stderr Log"** panel, and **"Retry Stage"** button to re-run only the failed stage.

### 6. `src/app/review/[job_id]/page.tsx`
- **Purpose:** Mockup inspection & draft listing publishing.
- **Features:**
  - Main Hero image showcase (`Hero.png`)
  - Full Gallery Grid displaying ALL 4 mockups with an interactive **Lightbox Modal** on click
  - Clickable PDF Download Card
  - Inline Metadata Editor (Title 140 max, Description, 13 Tags chip manager)
  - Connected Shop selector & **"Push Draft Listing to Etsy Shop"** CTA button.

### 7. `src/app/settings/page.tsx`
- **Purpose:** User profile & key store settings.
- **Sections:** Profile info, GCP Compute Engine GPU VM config, and AES-256 encrypted AI Provider API keys (Gemini 2.5 Flash, Replicate).

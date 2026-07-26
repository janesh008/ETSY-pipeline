# CraftDesk Web Frontend — User Experience & Business Workflow Architecture

## 🎯 Business Ergonomics & Seller Focus

`craftdesk_web` is designed around the daily operational workflow of an Etsy digital clipart seller. The application eliminates cognitive overhead, reduces administrative clicks, and prevents costly user mistakes:

1. **Editorial Atelier Aesthetics:** Built on a warm ivory paper background (`#F7F6F0`) with sand surface cards (`#EFECE6`), terracotta primary CTAs (`#C85A32`), and deep emerald badges (`#0D5C46`). The visual language feels like a premium artisan workshop rather than a generic dark-mode developer dashboard.
2. **Clear Infrastructure Visibility:** The GPU VM status widget is accessible directly from the dashboard and pipeline views, giving sellers real-time visibility into cloud compute state (`Stopped 🔴` / `Booting ComfyUI... ⚙️` / `Ready ✅ (:8188)`) so they never launch pipelines against an offline server.
3. **One-Click Handoffs:** Sellers move seamlessly through the 4-phase business workflow:
   `Prompt Studio` → `6-Stage Pipeline` → `Mockup Gallery Review` → `Push Draft to Etsy`.

---

## 🔄 Seller Workflow Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 1. PROMPT STUDIO                                       │
│  Input Theme / Etsy Link / Reference Images ──> Synthesize Matrix ──> Download .txt    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ One-Click Handoff
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               2. 6-STAGE PIPELINE                                      │
│  Auto-check GPU VM ──> Image Gen ──> BG Remove ──> Upscale ──> Mockups ──> PDF ──> Meta│
│  (If stage fails: Inspect root exception ──> Click "Retry Stage" without losing data)  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Auto Handoff on Complete
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          3. MOCKUP REVIEW & ETSY PUBLISHER                             │
│  Inspect Hero.png & 4 Mockups (Lightbox) ──> Edit Title/Description/Tags ──> Push Draft│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Client Security & Session Lifecycle

- **JWT Persistence:** Access tokens (60 min) and Refresh tokens (30 days) are persisted in `localStorage`.
- **Protected Route Middleware:** Unauthenticated attempts to access protected routes automatically trigger redirect to `/login`.
- **PKCE OAuth Safety:** The frontend generates cryptographic PKCE verifiers in `sessionStorage` during Etsy shop connection, ensuring authorization codes cannot be intercepted.

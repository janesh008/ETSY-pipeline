# CraftDesk Web Frontend — High-Level Architecture & User Experience

## 🎯 Scope & Responsibility

`craftdesk_web` is the single-page application (SPA) frontend for CraftDesk built with **Next.js 14 App Router**, **TypeScript**, **Tailwind CSS**, and **lucide-react**. It provides Etsy sellers with a visual workspace to generate AI clipart prompts, monitor GCP GPU VM compute status, execute 6-stage asset pipelines, review mockup galleries, edit listing metadata, and publish draft listings to Etsy shops.

---

## 🎨 Design System — Editorial Atelier

The interface strictly adheres to the **Editorial Atelier** theme:

```
┌─────────────────────────────────────────────────────────────┐
│                    Warm Ivory (#F7F6F0)                      │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           Sand Surface Card (#EFECE6)               │   │
│   │   ┌─────────────────────────────────────────────┐   │   │
│   │   │     Elevated Paper Input (#F9F8F3)          │   │   │
│   │   └─────────────────────────────────────────────┘   │   │
│   │   Primary Action CTA: Terracotta Rust (#C85A32)     │   │
│   │   Secondary Badge: Deep Emerald (#0D5C46)           │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Color Palette Tokens
- **`--color-ivory` (`#F7F6F0`):** Page background — warm paper.
- **`--color-sand` (`#EFECE6`):** Elevated cards, modals, and container panels.
- **`--color-paper` (`#F9F8F3`):** Input fields, textareas, and active hover states.
- **`--color-border-warm` (`#DCD8CF`):** Card borders and dividers.
- **`--color-charcoal` (`#1C2421`):** Primary text and headings.
- **`--color-slate-muted` (`#5A6561`):** Subtext, labels, and placeholders.
- **`--color-terracotta` (`#C85A32`):** Primary buttons, brand mark, key CTAs.
- **`--color-emerald-deep` (`#0D5C46`):** Success indicators, connected badges.

### Typography
- **Headings:** `Outfit` (sans-serif, display weight)
- **Body:** `Inter` (sans-serif, clean interface text)
- **Prompts & Logs:** `JetBrains Mono` (monospace, prompt matrix, stderr logs)

---

## 🔑 Session & Authentication Architecture

- Managed via `AuthProvider` React Context (`src/context/AuthContext.tsx`).
- Stores `craftdesk_access_token` and `craftdesk_refresh_token` in `localStorage`.
- Automatically redirects unauthenticated users attempting to access protected routes (`/dashboard`, `/prompt-studio`, `/shops`, `/pipeline`, `/review`, `/settings`) back to `/login`.

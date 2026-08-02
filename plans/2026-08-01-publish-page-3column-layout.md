# Implementation Plan — CraftDesk 3-Column Enterprise Workspace Layout Redesign

## Problem Statement
The current shop workspace uses a stacked top-to-bottom layout with a full-width header and top sub-navigation bar, taking up excessive vertical screen space and forcing unnecessary scrolling. The user requested a 3-column layout where the store switcher and security status sit inside a compact left sidebar, the primary listing form occupies the center panel with a compact mode switcher, and the GCS Theme Selector occupies a resizable right panel.

---

## Proposed Approach
Redesign the Next.js workspace shell and publish module into a high-performance 3-column SaaS dashboard:

1. **Left Sidebar Navigation Rail (`craftdesk_web/src/app/shops/[slug]/layout.tsx`):**
   - **Header Card:** Integrated Store Switcher dropdown (`PixelBarStudio`), `← Stores` back button, external Etsy link icon `↗`, and `AES-256 Active` security badge.
   - **Navigation Links:** Vertical list (`Overview`, `Publish Listings`, `AI Listing Optimizer`, `Active Listings`, `Settings & Tokens`) with active pill highlights and micro-animations.
   - **Footer Badge:** GCS connection status.

2. **Center Panel — Main Workspace (`craftdesk_web/src/app/shops/[slug]/publish/page.tsx`):**
   - **Top Mode Segmented Bar:** Ultra-compact pill control (`📦 GCS Theme Browser` | `📤 Manual File Upload` | `🪄 Gemini Vision AI`).
   - **Center Panel Form:** **Listing Metadata & Price Overrides** (Title with AI generator button, Description, Tags chip manager, Price & Stock inputs, and direct Publish to Etsy button).

3. **Right Sidebar Panel — Resizable GCS Theme Selector (`craftdesk_web/src/components/gcs/EnterpriseGcsThemeSelector.tsx`):**
   - Resizable left-drag handle (`panelWidth` state between 320px and 550px).
   - Search bar + Date filters + Multi-select checkboxes + Floating batch action bar.

---

## Files / Modules Touched
- [MODIFY] [`craftdesk_web/src/app/shops/[slug]/layout.tsx`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/[slug]/layout.tsx)
- [MODIFY] [`craftdesk_web/src/app/shops/[slug]/publish/page.tsx`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/[slug]/publish/page.tsx)
- [MODIFY] [`craftdesk_web/src/components/gcs/EnterpriseGcsThemeSelector.tsx`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/components/gcs/EnterpriseGcsThemeSelector.tsx)

---

## Risks & Edge Cases
- **Responsive Layout:** On smaller screens (<1024px), right sidebar should stack cleanly or collapse gracefully.
- **Drag Resize Handle:** Ensure mouse event listeners (`mousemove`, `mouseup`) detach properly to prevent event memory leaks.

---

## Ordered Implementation Steps

### Step 1: Update Workspace Layout Shell (`layout.tsx`)
- Move store switcher, Etsy external link icon, and security status into the top of the Left Sidebar.
- Move top navigation tabs into vertical links inside the left sidebar.

### Step 2: Redesign Publish Page Layout (`publish/page.tsx`)
- Move mode switcher into a compact top segmented control above the center form.
- Place **Listing Metadata & Price Overrides** in the center main viewport.
- Place **Enterprise GCS Theme Selector** in the right column with a resizable handle.

### Step 3: Enhance GCS Theme Selector Component (`EnterpriseGcsThemeSelector.tsx`)
- Add resizable width controls and compact view toggles.

### Step 4: Verification & Build
- Run `npm run build` in `craftdesk_web` to verify zero type or build errors.

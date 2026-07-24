# CraftDesk Web Frontend — Coding Rules & Component Standards

## 📜 Development Standards

1. **Client Components:** Pages requiring state, hooks (`useState`, `useEffect`), or browser APIs (`localStorage`, `sessionStorage`, `navigator.clipboard`) must declare `"use client";` at the very first line of the file.
2. **Icons:** Use `lucide-react` icons. Never import icons from external fonts or raw SVG strings unless necessary.
3. **No Hardcoded API URLs:** API requests must use `src/lib/api.ts` or read `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`.
4. **Form Controls:** All form inputs must feature explicit `<label>` tags with `uppercase tracking-wider text-xs text-[#5A6561]` styling.

---

## 🎨 Theme Token Rules

When building UI components, strictly follow these Tailwind CSS token mappings:

```tsx
// Page container
<div className="bg-[#F7F6F0] text-[#1C2421]">

// Card / Panel
<div className="bg-[#EFECE6] border border-[#DCD8CF] rounded-2xl p-6 shadow-sm">

// Input Field
<input className="bg-[#F9F8F3] border border-[#DCD8CF] rounded-xl text-xs text-[#1C2421] focus:ring-[#C85A32]/40" />

// Primary Button (Terracotta)
<button className="bg-[#C85A32] hover:bg-[#B24D28] text-white font-semibold text-xs rounded-xl shadow-sm">

// Secondary Badge (Emerald)
<span className="bg-[#E6F2EE] text-[#0D5C46] text-xs font-bold rounded-full px-2.5 py-0.5">
```

---

## ⚠️ GOTCHAS & Pitfalls

### 1. Next.js 15+ Dynamic Route Parameters
- **Problem:** In Next.js 15+, `params` in dynamic page routes (`/review/[job_id]/page.tsx`) is a `Promise`. Direct property access (`params.job_id`) causes runtime errors.
- **Rule:** Unwrap `params` using `React.use()` or `await`:
  ```tsx
  import React, { use } from "react";
  export default function ReviewPage({ params }: { params: Promise<{ job_id: string }> }) {
    const { job_id } = use(params);
    ...
  }
  ```

### 2. File Download Triggers
- **Problem:** Plain `window.location.href` triggers full page reloads when downloading files.
- **Rule:** Use Blob URLs and invisible anchor elements:
  ```tsx
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  ```

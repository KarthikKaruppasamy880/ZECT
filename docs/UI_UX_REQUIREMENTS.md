# ZECT — UI/UX Requirements

## Overview

All ZECT screens must be mobile-compatible, browser-compatible, device-reflexive, and accessible. This document defines the requirements for responsive design, collapsible navigation, code generation visibility, and cross-device support.

---

## Responsive Design Requirements

### Breakpoints

| Breakpoint | Width | Target Device |
|-----------|-------|---------------|
| `xs` | <640px | Mobile portrait |
| `sm` | ≥640px | Mobile landscape |
| `md` | ≥768px | Tablet |
| `lg` | ≥1024px | Desktop |
| `xl` | ≥1280px | Large desktop |
| `2xl` | ≥1536px | Ultra-wide |

### Layout Rules

| Screen Size | Sidebar | Content | Cards |
|-------------|---------|---------|-------|
| Mobile (<768px) | Hidden (hamburger menu) | Full width | Single column |
| Tablet (768-1024px) | Collapsed (icons only) | Full width minus sidebar | 2 columns |
| Desktop (≥1024px) | Expanded (icons + labels) | Full width minus sidebar | 3-4 columns |

---

## Collapsible Navigation

### Requirements

1. **Toggle button** — Visible button to collapse/expand sidebar
2. **Collapsed state** — Shows icons only (no labels), narrow width (~64px)
3. **Expanded state** — Shows icons + labels, standard width (~256px)
4. **State persistence** — Remember collapse state across page navigation
5. **Mobile behavior** — Sidebar hidden by default, opens as overlay on hamburger click
6. **Keyboard shortcut** — `Ctrl+B` or `Cmd+B` to toggle
7. **Smooth animation** — CSS transition on width change (200ms ease)

### Implementation

```tsx
// Sidebar collapse state
const [collapsed, setCollapsed] = useState(() => {
  return localStorage.getItem('sidebar-collapsed') === 'true';
});

// Toggle handler
const toggleSidebar = () => {
  setCollapsed(!collapsed);
  localStorage.setItem('sidebar-collapsed', String(!collapsed));
};

// Sidebar width
<aside className={collapsed ? 'w-16' : 'w-64'} style={{ transition: 'width 200ms ease' }}>
  {collapsed ? <IconOnlyNav /> : <FullNav />}
</aside>
```

### Mobile Overlay

```tsx
// Mobile: sidebar as overlay
<div className="md:hidden">
  <button onClick={toggleMobile}>☰</button>
  {mobileOpen && (
    <div className="fixed inset-0 z-50 bg-black/50" onClick={closeMobile}>
      <aside className="w-64 h-full bg-slate-900">
        <FullNav />
      </aside>
    </div>
  )}
</div>
```

---

## Code Generation Visibility

### Requirements

1. **Generated code must be visible on-screen** — users need to see what was generated
2. **Syntax highlighting** — proper code highlighting by language
3. **Copy button** — one-click copy to clipboard
4. **Scrollable** — long outputs scrollable within a fixed-height container
5. **Expandable** — option to expand to full-screen view
6. **Download** — option to download as file

### Where Code is Generated

| Page | What's Generated | Display Method |
|------|-----------------|----------------|
| Ask Mode | Code snippets in answers | Inline code blocks |
| Plan Mode | Implementation plan with code | Markdown with code blocks |
| Blueprint | Full project prompt | Large scrollable panel |
| Doc Generator | Documentation sections | Tabbed sections |
| Code Review | Fix prompts | Dedicated output panel |

### Code Display Component

```tsx
interface CodeOutputProps {
  code: string;
  language: string;
  title?: string;
  maxHeight?: string;
}

function CodeOutput({ code, language, title, maxHeight = '400px' }: CodeOutputProps) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700">
      {/* Header with title + actions */}
      <div className="flex justify-between items-center px-4 py-2 border-b border-slate-700">
        <span className="text-sm text-slate-400">{title || language}</span>
        <div className="flex gap-2">
          <button onClick={copyToClipboard}>Copy</button>
          <button onClick={expandFullScreen}>Expand</button>
          <button onClick={downloadFile}>Download</button>
        </div>
      </div>
      
      {/* Code content */}
      <pre className="overflow-auto p-4" style={{ maxHeight }}>
        <code className={`language-${language}`}>
          {code}
        </code>
      </pre>
    </div>
  );
}
```

---

## Browser Compatibility

### Required Support

| Browser | Minimum Version | Notes |
|---------|----------------|-------|
| Chrome | 90+ | Primary target |
| Firefox | 88+ | Full support |
| Safari | 14+ | Including iOS Safari |
| Edge | 90+ | Chromium-based |
| Samsung Internet | 15+ | Mobile |
| Opera | 76+ | Chromium-based |

### CSS Compatibility

- Use `@supports` for progressive enhancement
- Avoid bleeding-edge CSS features without fallbacks
- Test flexbox and grid layouts across browsers
- Use autoprefixer for vendor prefixes

### JavaScript Compatibility

- Target ES2020 (supported by all minimum browser versions)
- Use optional chaining (`?.`) and nullish coalescing (`??`)
- Avoid `structuredClone` without polyfill (Safari 15.4+)

---

## Device Reflexive Design

### What "Device Reflexive" Means

The UI automatically adapts to:
1. **Screen size** — layout changes at breakpoints
2. **Input method** — touch-friendly targets on mobile
3. **Orientation** — landscape/portrait handling
4. **Pixel density** — sharp icons/text on Retina/HiDPI
5. **Connection speed** — lazy-load non-critical content

### Touch Target Sizes

| Element | Minimum Size | Spacing |
|---------|-------------|---------|
| Buttons | 44×44px | 8px between |
| Links (inline) | 44px height | 4px between |
| Form inputs | 48px height | 12px between |
| Sidebar items | 48px height | 4px between |
| Dropdown items | 44px height | 0px (grouped) |

### Mobile-Specific Adaptations

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Sidebar | Fixed left, always visible | Hidden, overlay on tap |
| Data tables | Full table view | Card view or horizontal scroll |
| Charts | Full size with legends | Simplified, touch-interactive |
| Forms | Multi-column layout | Single column, full width |
| Modals | Centered overlay (600px wide) | Full screen sheet |
| Code blocks | Fixed height, scrollable | Full height, scrollable |

---

## Accessibility (WCAG 2.1 AA)

### Requirements

| Criterion | Requirement |
|-----------|-------------|
| Color contrast | 4.5:1 for text, 3:1 for large text |
| Focus indicators | Visible focus ring on all interactive elements |
| Keyboard navigation | All features accessible via keyboard |
| Screen reader | Proper ARIA labels and roles |
| Alt text | All images have meaningful alt text |
| Form labels | All inputs have associated labels |
| Error messages | Clear, specific error descriptions |
| Animations | Respect `prefers-reduced-motion` |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | <1.5s | Lighthouse |
| Largest Contentful Paint | <2.5s | Lighthouse |
| Time to Interactive | <3.0s | Lighthouse |
| Cumulative Layout Shift | <0.1 | Lighthouse |
| Bundle size (gzipped) | <500KB | Build output |

---

## Current Gaps (To Be Implemented)

| Gap | Priority | Effort |
|-----|----------|--------|
| Sidebar not collapsible | High | 2-3 hours |
| No mobile hamburger menu | High | 2-3 hours |
| Code output not visible in Ask/Plan Mode | High | 3-4 hours |
| Tables not responsive on mobile | Medium | 2 hours |
| Charts not touch-interactive | Medium | 2 hours |
| No keyboard shortcuts | Low | 3-4 hours |
| No dark/light theme toggle | Low | 4-5 hours |
| No loading skeletons | Low | 2-3 hours |

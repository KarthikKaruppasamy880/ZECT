import { useLayoutEffect, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

type HeaderDropdownPortalProps = {
  open: boolean;
  anchorRef: RefObject<HTMLElement | HTMLDivElement | null>;
  children: ReactNode;
  testId?: string;
  className?: string;
};

/**
 * Header overflow-x-auto clips absolute menus. Portal to document.body with fixed coords.
 */
export default function HeaderDropdownPortal({
  open,
  anchorRef,
  children,
  testId,
  className,
}: HeaderDropdownPortalProps) {
  const [pos, setPos] = useState({ top: 0, left: 0, minWidth: 160 });

  useLayoutEffect(() => {
    if (!open) return;
    const el = anchorRef.current;
    if (!el) return;
    const update = () => {
      const r = el.getBoundingClientRect();
      setPos({ top: r.bottom + 4, left: r.left, minWidth: Math.max(r.width, 160) });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, anchorRef]);

  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div
      data-testid={testId}
      className={className}
      style={{ position: "fixed", top: pos.top, left: pos.left, minWidth: pos.minWidth, zIndex: 80 }}
    >
      {children}
    </div>,
    document.body,
  );
}

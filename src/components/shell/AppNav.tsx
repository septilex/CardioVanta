"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { NAV_BACK, NAV_LATERAL } from "../../lib/motion";
import "../../app/app-shell.css";

interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
}

const iconProps = {
  className: "ax-nav-icon",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

/** The four sections of the app, in sidebar order. Overview is the landing page. */
export const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Overview",
    icon: (
      <svg {...iconProps}>
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    href: "/assessment",
    label: "Heart Analysis",
    icon: (
      <svg {...iconProps}>
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        <polyline points="3.5 12 8.5 12 10.5 8 13.5 16 15.5 12 20.5 12" />
      </svg>
    ),
  },
  {
    href: "/research",
    label: "Research",
    icon: (
      <svg {...iconProps}>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },
  {
    href: "/about",
    label: "About",
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  },
];

/** Overview (the landing page) is "back"; moves between app sections cross-fade in place. */
function transitionFor(href: string) {
  return href === "/" ? [NAV_BACK] : [NAV_LATERAL];
}

function useActiveHref() {
  const pathname = usePathname() ?? "";
  return NAV_ITEMS.find((item) => item.href !== "/" && (pathname === item.href || pathname.startsWith(`${item.href}/`)))
    ?.href;
}

/** Desktop sidebar (hidden at 900px and below, where MobileNav takes over). */
export function AppSidebar() {
  const active = useActiveHref();
  return (
    <aside className="ax-sidebar">
      <div className="ax-sidebar-top">
        <Link href="/" transitionTypes={[NAV_BACK]} className="ax-sidebar-logo-link" title="CardioVanta Home">
          <img
            src="/brand/cardiovanta-horizontal-transparent.png"
            alt="CardioVanta | Intelligent Cardiovascular Insight"
            className="ax-sidebar-logo"
          />
        </Link>
        <nav className="ax-nav" aria-label="Main Navigation">
          {NAV_ITEMS.map((item) => {
            const isActive = item.href === active;
            return (
              <Link
                key={item.href}
                href={item.href}
                transitionTypes={transitionFor(item.href)}
                className={isActive ? "ax-nav-item ax-nav-active" : "ax-nav-item"}
                aria-current={isActive ? "page" : undefined}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="ax-sidebar-heart-wrap" aria-hidden="true">
        <img src="/images/anatomical-heart.jpg" alt="" className="ax-sidebar-heart-img" />
      </div>
    </aside>
  );
}

/** Compact section bar for narrow screens, where the sidebar is hidden. */
export function MobileNav() {
  const active = useActiveHref();
  return (
    <nav className="app-mnav" aria-label="Sections">
      {NAV_ITEMS.map((item) => {
        const isActive = item.href === active;
        return (
          <Link
            key={item.href}
            href={item.href}
            transitionTypes={transitionFor(item.href)}
            className={isActive ? "app-mnav-item is-active" : "app-mnav-item"}
            aria-current={isActive ? "page" : undefined}
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

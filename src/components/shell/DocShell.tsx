import Link from "next/link";
import type { ReactNode } from "react";
import { AppSidebar, MobileNav } from "./AppNav";
import { RouteTransition } from "../motion/RouteTransition";
import { NAV_LATERAL } from "../../lib/motion";
import "../../app/doc-page.css";

/** Frame for the Research and About pages: shared navigation, breadcrumb bar, page transition. */
export function DocShell({ section, children }: { section: string; children: ReactNode }) {
  return (
    <RouteTransition>
      <div className="cv-doc-shell">
        <AppSidebar />
        <div className="cv-doc-main">
          <MobileNav />
          <header className="doc-topbar">
            <p className="doc-crumbs">
              <Link href="/">CardioVanta</Link> / {section}
            </p>
            <Link href="/assessment" transitionTypes={[NAV_LATERAL]} className="doc-cta">
              Open Heart Analysis <span aria-hidden="true">→</span>
            </Link>
          </header>
          <main>{children}</main>
        </div>
      </div>
    </RouteTransition>
  );
}

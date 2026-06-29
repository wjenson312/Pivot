"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { METHODS_REGISTRY } from "@/lib/methods-registry";

export default function TabNav() {
  const pathname = usePathname();

  return (
    <nav className="tab-nav">
      <Link
        href="/database"
        className={`tab-nav__link ${pathname === "/database" ? "tab-nav__link--active" : ""}`}
      >
        Database
      </Link>
      {METHODS_REGISTRY.map((m) => {
        const href = `/methods/${m.id}`;
        const active = pathname === href;
        if (!m.ready) {
          return (
            <span key={m.id} className="tab-nav__link tab-nav__link--disabled" title="Not ready yet">
              {m.navLabel}
            </span>
          );
        }
        return (
          <Link
            key={m.id}
            href={href}
            className={`tab-nav__link ${active ? "tab-nav__link--active" : ""}`}
          >
            {m.navLabel}
          </Link>
        );
      })}
    </nav>
  );
}

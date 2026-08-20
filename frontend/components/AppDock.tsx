"use client";

import { usePathname } from "next/navigation";
import { FloatingDock } from "@/components/ui/floating-dock";
import { METHODS_REGISTRY } from "@/lib/methods-registry";
import {
  IconHome,
  IconDatabase,
  IconActivity,
  IconArrowsMaximize,
  IconBolt,
} from "@tabler/icons-react";

// Icon per method id — kept separate from methods-registry.ts so that file
// stays a plain data source with no JSX/React-icon dependency.
const METHOD_ICONS: Record<string, typeof IconActivity> = {
  "knee-rotation-load": IconActivity,
  "range-of-motion": IconArrowsMaximize,
  "landing-mechanics": IconBolt,
};

const NAV_ITEMS = [
  { title: "Home", href: "/", Icon: IconHome },
  { title: "Database", href: "/database", Icon: IconDatabase },
  ...METHODS_REGISTRY.filter((m) => m.ready).map((m) => ({
    title: m.navLabel,
    href: `/methods/${m.id}`,
    Icon: METHOD_ICONS[m.id] ?? IconActivity,
  })),
];

export default function AppDock() {
  const pathname = usePathname();

  const items = NAV_ITEMS.map(({ title, href, Icon }) => {
    const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
    return {
      title,
      href,
      active,
      icon: <Icon className={active ? "h-full w-full text-white" : "h-full w-full text-neutral-400"} />,
    };
  });

  return (
    <div className="fixed inset-x-0 bottom-6 z-50 flex justify-center pointer-events-none">
      <div className="pointer-events-auto">
        <FloatingDock
          items={items}
          desktopClassName="border border-[#363739] bg-[#07080a]/90 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.55)]"
          mobileClassName="fixed bottom-6 right-6"
        />
      </div>
    </div>
  );
}

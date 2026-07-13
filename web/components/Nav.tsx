"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: [string, string][] = [
  ["/dashboard", "Dashboard"],
  ["/calls", "Calls"],
  ["/calendar", "Calendar"],
  ["/playground", "Playground"],
  ["/configuration", "Configuration"],
  ["/integrations", "Integrations"],
  ["/settings", "Settings"],
];

export function Nav() {
  const path = usePathname();
  return (
    <nav>
      {LINKS.map(([href, label]) => (
        <Link
          key={href}
          href={href}
          className="rb-navlink"
          data-active={path === href || path?.startsWith(href + "/")}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

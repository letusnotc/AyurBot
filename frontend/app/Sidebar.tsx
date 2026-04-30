"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageCircle, LayoutList } from "lucide-react";

const NAV = [
  { href: "/", icon: MessageCircle, label: "Chat" },
  { href: "/compare", icon: LayoutList, label: "Compare" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full z-50 flex flex-col items-center py-6 gap-4 w-[64px] bg-[#2a1b18]/90 backdrop-blur-md border-r border-[#5d4037]/40">
      {NAV.map(({ href, icon: Icon, label }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            title={label}
            className={`flex flex-col items-center justify-center w-11 h-11 rounded-xl transition-all ${
              active
                ? "bg-[#2d5a27] text-[#f4ece1]"
                : "text-[#f4ece1]/50 hover:bg-[#f4ece1]/10 hover:text-[#f4ece1]"
            }`}
          >
            <Icon className="h-5 w-5" />
            <span className="text-[8px] font-black uppercase tracking-wider mt-0.5">
              {label}
            </span>
          </Link>
        );
      })}
    </aside>
  );
}

import { NavLink } from "react-router-dom";
import { Compass, FileText, User } from "lucide-react";
import { cn } from "@/lib/utils";

export function BottomNav() {
  const navItems = [
    { to: "/home", label: "Home", icon: Compass },
    { to: "/requests", label: "Requests", icon: FileText },
    { to: "/profile", label: "Profile", icon: User },
  ];

  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-brand-dark-card/95 border-t border-gray-200/80 dark:border-brand-dark-border backdrop-blur-md pb-safe"
    >
      <div className="flex items-center justify-around h-16 px-2 max-w-md mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center justify-center flex-1 h-full min-w-[44px] min-h-[44px] text-xs font-medium transition-colors select-none",
                  isActive
                    ? "text-brand-primary dark:text-teal-400 font-semibold"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div
                    className={cn(
                      "p-1 rounded-xl transition-all",
                      isActive && "bg-teal-50 dark:bg-brand-dark-muted/40"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="mt-0.5">{item.label}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}

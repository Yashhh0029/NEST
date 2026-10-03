import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { ThemeToggle } from "./ThemeToggle";
import { NotificationBell } from "./NotificationBell";
import {
  Compass,
  LogOut,
  PlusCircle,
  User,
  FileText,
  Users,
  Calendar,
  MapPin,
  ShieldAlert,
  MessageSquare,
  Menu,
  X,
} from "lucide-react";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile drawer when route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileMenuOpen]);

  const handleLogout = () => {
    setMobileMenuOpen(false);
    logout();
    navigate("/login");
  };

  const navLinks = [
    { to: "/home", label: "New Request", icon: PlusCircle },
    { to: "/requests", label: "Requests", icon: FileText },
    { to: "/connections", label: "Connections", icon: Users },
    { to: "/sessions", label: "Sessions", icon: Calendar },
    { to: "/resources", label: "Resources", icon: MapPin },
    { to: "/community", label: "Community", icon: MessageSquare },
    { to: "/profile", label: "Profile", icon: User },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200/80 dark:border-brand-dark-border bg-white/90 dark:bg-brand-dark/90 backdrop-blur-md transition-colors">
      <div className="max-w-6xl mx-auto px-3.5 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          to={isAuthenticated ? "/home" : "/"}
          className="flex items-center gap-2 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary rounded-xl p-1"
        >
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-brand-primary flex items-center justify-center text-white shadow-soft group-hover:scale-105 transition-transform shrink-0">
            <Compass className="w-5 h-5 text-amber-300" />
          </div>
          <div className="min-w-0">
            <span className="font-heading font-extrabold text-lg sm:text-xl tracking-tight text-gray-900 dark:text-gray-100 flex items-center gap-1">
              NEST
            </span>
            <span className="hidden sm:block text-[10px] uppercase font-bold tracking-wider text-brand-primary dark:text-teal-400 -mt-1">
              Community Matching
            </span>
          </div>
        </Link>

        {/* Right Navigation */}
        <div className="flex items-center gap-1.5 sm:gap-3">
          {isAuthenticated ? (
            <>
              {/* Desktop Links */}
              <nav className="hidden md:flex items-center gap-1 mr-2" aria-label="Main Navigation">
                {navLinks.map((link) => {
                  const Icon = link.icon;
                  const isActive = location.pathname === link.to;
                  return (
                    <Link
                      key={link.to}
                      to={link.to}
                      className={`px-3 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-1.5 ${
                        isActive
                          ? "bg-teal-50 dark:bg-brand-dark-card text-brand-primary dark:text-teal-300 font-semibold"
                          : "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card"
                      }`}
                    >
                      <Icon className="w-4 h-4 text-brand-primary" />
                      {link.label}
                    </Link>
                  );
                })}
                {user?.role === "admin" && (
                  <Link
                    to="/admin/reports"
                    className={`px-3 py-2 text-sm font-semibold rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors flex items-center gap-1.5 ${
                      location.pathname.startsWith("/admin") ? "bg-rose-50 dark:bg-rose-950/40" : ""
                    }`}
                  >
                    <ShieldAlert className="w-4 h-4" />
                    Admin
                  </Link>
                )}
              </nav>

              <div className="flex items-center gap-1 sm:gap-2">
                <NotificationBell />
                <ThemeToggle />

                {/* Sign Out (Desktop) */}
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="hidden md:flex p-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-brand-danger transition-colors min-h-[44px] min-w-[44px] items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-danger"
                >
                  <LogOut className="w-5 h-5" />
                </button>

                {/* Mobile Menu Hamburger Button */}
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
                  aria-expanded={mobileMenuOpen}
                  className="md:hidden p-2 rounded-xl border border-gray-200 dark:border-brand-dark-border text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
                >
                  {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-1.5 sm:gap-3">
              <ThemeToggle />
              <Link
                to="/login"
                className="px-2.5 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors min-h-[44px] flex items-center"
              >
                Log In
              </Link>
              <Link
                to="/register"
                className="px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-xl bg-brand-primary text-white hover:bg-brand-primary-hover shadow-soft transition-colors min-h-[44px] flex items-center"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Drawer Menu (Authenticated) */}
      {isAuthenticated && mobileMenuOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 top-16 z-50 md:hidden bg-black/40 backdrop-blur-xs flex flex-col justify-start"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div
            className="w-full max-h-[calc(100dvh-4rem)] overflow-y-auto bg-white dark:bg-brand-dark border-b border-gray-200 dark:border-brand-dark-border p-4 shadow-xl space-y-4 animate-in slide-in-from-top-2 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* User Profile Summary */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-brand-dark-border">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-teal-100 dark:bg-brand-dark-muted text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold font-heading shrink-0">
                  {user?.name?.charAt(0) || "U"}
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-sm text-gray-900 dark:text-gray-100 truncate">
                    {user?.name || "Community Member"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                    {user?.role || "Member"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Navigation Links Grid */}
            <nav className="grid grid-cols-1 gap-1" aria-label="Mobile Drawer Navigation">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = location.pathname === link.to;
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`px-3.5 py-3 rounded-xl text-sm font-medium transition-colors flex items-center gap-3 min-h-[44px] ${
                      isActive
                        ? "bg-teal-50 dark:bg-brand-dark-card text-brand-primary dark:text-teal-300 font-semibold"
                        : "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card"
                    }`}
                  >
                    <div className="p-1 rounded-lg bg-teal-50 dark:bg-brand-dark-muted/40 text-brand-primary dark:text-teal-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span>{link.label}</span>
                  </Link>
                );
              })}

              {user?.role === "admin" && (
                <Link
                  to="/admin/reports"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-3 rounded-xl text-sm font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors flex items-center gap-3 min-h-[44px] ${
                    location.pathname.startsWith("/admin") ? "bg-rose-50 dark:bg-rose-950/40" : ""
                  }`}
                >
                  <div className="p-1 rounded-lg bg-rose-100 dark:bg-rose-950/50 text-rose-600">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <span>Admin Reports</span>
                </Link>
              )}
            </nav>

            {/* Sign Out Button */}
            <div className="pt-2 border-t border-gray-100 dark:border-brand-dark-border">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full px-3.5 py-3 rounded-xl text-sm font-medium text-brand-danger hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors flex items-center gap-3 min-h-[44px]"
              >
                <div className="p-1 rounded-lg bg-red-50 dark:bg-red-950/50 text-brand-danger">
                  <LogOut className="w-4 h-4" />
                </div>
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

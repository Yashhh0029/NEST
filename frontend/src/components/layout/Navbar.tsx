import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { ThemeToggle } from "./ThemeToggle";
import {
  Compass,
  LogOut,
  PlusCircle,
  User,
  FileText,
  Users,
  MapPin,
  ShieldAlert,
} from "lucide-react";

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200/80 dark:border-brand-dark-border bg-white/90 dark:bg-brand-dark/90 backdrop-blur-md transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          to={isAuthenticated ? "/home" : "/"}
          className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary rounded-xl p-1"
        >
          <div className="w-10 h-10 rounded-xl bg-brand-primary flex items-center justify-center text-white shadow-soft group-hover:scale-105 transition-transform">
            <Compass className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <span className="font-heading font-extrabold text-xl tracking-tight text-gray-900 dark:text-gray-100 flex items-center gap-1">
              NEST
            </span>
            <span className="hidden sm:block text-[10px] uppercase font-bold tracking-wider text-brand-primary dark:text-teal-400 -mt-1">
              Community Matching
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <div className="flex items-center gap-2 sm:gap-4">
          {isAuthenticated ? (
            <>
              <nav className="hidden md:flex items-center gap-1 mr-2" aria-label="Main Navigation">
                <Link
                  to="/home"
                  className="px-3.5 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors flex items-center gap-1.5"
                >
                  <PlusCircle className="w-4 h-4 text-brand-primary" />
                  New Request
                </Link>
                <Link
                  to="/requests"
                  className="px-3.5 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors flex items-center gap-1.5"
                >
                  <FileText className="w-4 h-4 text-brand-primary" />
                  Requests
                </Link>
                <Link
                  to="/connections"
                  className="px-3.5 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors flex items-center gap-1.5"
                >
                  <Users className="w-4 h-4 text-brand-primary" />
                  Connections
                </Link>
                <Link
                  to="/resources"
                  className="px-3.5 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors flex items-center gap-1.5"
                >
                  <MapPin className="w-4 h-4 text-brand-primary" />
                  Resources
                </Link>
                <Link
                  to="/profile"
                  className="px-3.5 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors flex items-center gap-1.5"
                >
                  <User className="w-4 h-4 text-brand-primary" />
                  Profile
                </Link>
                {user?.role === "admin" && (
                  <Link
                    to="/admin/reports"
                    className="px-3.5 py-2 text-sm font-semibold rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors flex items-center gap-1.5"
                  >
                    <ShieldAlert className="w-4 h-4" />
                    Admin
                  </Link>
                )}
              </nav>

              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="p-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-brand-danger transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-danger"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 sm:gap-3">
              <ThemeToggle />
              <Link
                to="/login"
                className="px-4 py-2 text-sm font-medium rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors min-h-[44px] flex items-center"
              >
                Log In
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 text-sm font-medium rounded-xl bg-brand-primary text-white hover:bg-brand-primary-hover shadow-soft transition-colors min-h-[44px] flex items-center"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

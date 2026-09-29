import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { BottomNav } from "./BottomNav";
import { ToastContainer } from "../ui/Toast";
import { useAuthStore } from "@/store/useAuthStore";

export function AppLayout() {
  const { isAuthenticated } = useAuthStore();

  return (
    <div className="min-h-screen flex flex-col bg-brand-light dark:bg-brand-dark text-gray-900 dark:text-gray-100 transition-colors">
      <Navbar />
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-12">
        <Outlet />
      </main>
      {isAuthenticated && <BottomNav />}
      <ToastContainer />
    </div>
  );
}

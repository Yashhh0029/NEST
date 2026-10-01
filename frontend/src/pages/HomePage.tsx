import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { requestsService } from "@/services/requests";
import { RequestBox } from "@/components/request/RequestBox";
import { RequestCard } from "@/components/request/RequestCard";
import { NearbyRequestsFeed } from "@/components/home/NearbyRequestsFeed";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Reveal } from "@/components/motion";
import type { NewcomerRequest } from "@/types/request";
import {
  Compass,
  Clock,
  ArrowRight,
  Sparkles,
  HeartHandshake,
} from "lucide-react";

export function HomePage() {
  const { user } = useAuthStore();
  const [recentRequests, setRecentRequests] = useState<NewcomerRequest[]>([]);

  // Default active tab based on user role
  const isHelperOnly = user?.role === "helper";
  const isBoth = user?.role === "both";
  const [activeTab, setActiveTab] = useState<"newcomer" | "helper">(
    isHelperOnly ? "helper" : "newcomer"
  );

  useEffect(() => {
    requestsService
      .getMyRequests()
      .then((data) => {
        setRecentRequests(data.slice(0, 4));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-2 sm:py-6 px-4">
      {/* Welcome Banner */}
      <Reveal direction="down">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold font-heading text-slate-900 dark:text-white flex items-center gap-2">
              <span>Hey, {user?.name?.split(" ")[0] || "Friend"}</span>
              <span className="text-2xl">👋</span>
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Welcome to NEST. Your neighborhood assistance and guidance hub.
            </p>
          </div>

          {/* Role switcher tab when user is 'both' */}
          {isBoth && (
            <div className="inline-flex p-1 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => setActiveTab("newcomer")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === "newcomer"
                    ? "bg-white dark:bg-slate-900 text-teal-700 dark:text-teal-300 shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Ask for Help</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("helper")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === "helper"
                    ? "bg-white dark:bg-slate-900 text-teal-700 dark:text-teal-300 shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                }`}
              >
                <HeartHandshake className="w-3.5 h-3.5" />
                <span>Help Others</span>
              </button>
            </div>
          )}
        </div>
      </Reveal>

      {/* Main Content Area */}
      {activeTab === "newcomer" && (
        <div className="space-y-8">
          {/* Natural Language Request Box */}
          <Reveal direction="up">
            <section aria-label="Request Assistance">
              <RequestBox />
            </section>
          </Reveal>

          {/* Engine Capability Banner */}
          <Reveal direction="up" delay={0.1}>
            <Card className="p-4 sm:p-5 rounded-2xl bg-teal-50/70 dark:bg-teal-950/30 border-teal-200/80 dark:border-teal-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="p-2.5 rounded-2xl bg-teal-600 text-white shadow-sm shrink-0">
                  <Compass className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold font-heading text-slate-900 dark:text-white flex items-center gap-2">
                    <span>Local Semantic Vector Search Active</span>
                    <Badge variant="primary" size="sm">pgvector</Badge>
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    Your request matches against enrolled guides with neighborhood embeddings and proven local expertise.
                  </p>
                </div>
              </div>

              <Link
                to="/requests"
                className="text-xs font-semibold text-teal-700 dark:text-teal-400 flex items-center gap-1 hover:underline whitespace-nowrap min-h-[36px]"
              >
                <span>View My Requests</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </Card>
          </Reveal>

          {/* Recent Requests Section */}
          {recentRequests.length > 0 && (
            <Reveal direction="up" delay={0.2}>
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-bold font-heading text-slate-900 dark:text-white flex items-center gap-2">
                    <Clock className="w-4 h-4 text-teal-600" />
                    <span>Your Recent Requests</span>
                  </h2>
                  <Link
                    to="/requests"
                    className="text-xs font-medium text-teal-700 dark:text-teal-400 hover:underline min-h-[32px] flex items-center"
                  >
                    See all ({recentRequests.length})
                  </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {recentRequests.map((req) => (
                    <RequestCard key={req.id} request={req} />
                  ))}
                </div>
              </section>
            </Reveal>
          )}

          {/* Also show Nearby Requests sneak peek if user is helper or both */}
          {(user?.role === "helper" || user?.role === "both") && (
            <Reveal direction="up" delay={0.3}>
              <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
                <NearbyRequestsFeed />
              </div>
            </Reveal>
          )}
        </div>
      )}

      {activeTab === "helper" && (
        <div className="space-y-8">
          <Reveal direction="up">
            <NearbyRequestsFeed />
          </Reveal>
        </div>
      )}
    </div>
  );
}

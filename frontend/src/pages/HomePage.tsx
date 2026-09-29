import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { requestsService } from "@/services/requests";
import { RequestBox } from "@/components/request/RequestBox";
import { RequestCard } from "@/components/request/RequestCard";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { NewcomerRequest } from "@/types/request";
import { Compass, Clock, ArrowRight } from "lucide-react";

export function HomePage() {
  const { user } = useAuthStore();
  const [recentRequests, setRecentRequests] = useState<NewcomerRequest[]>([]);

  useEffect(() => {
    requestsService
      .getMyRequests()
      .then((data) => {
        setRecentRequests(data.slice(0, 3));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-2 sm:py-6">
      {/* Welcome Banner */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
          Hey, {user?.name?.split(" ")[0] || "Friend"} 👋
        </h1>
        <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400">
          Tell NEST what you need in your city, or explore community requests.
        </p>
      </div>

      {/* Main Natural Language Request Box */}
      <section aria-label="Request Assistance">
        <RequestBox />
      </section>

      {/* Honest Matching Engine Notice */}
      <Card className="p-4 sm:p-5 bg-teal-50/50 dark:bg-brand-dark-muted/20 border-teal-100 dark:border-brand-dark-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-100 dark:bg-brand-dark-muted text-brand-primary dark:text-teal-300">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
              <span>Local Semantic Vector Search Enabled</span>
              <Badge variant="primary" size="sm">Phase 4 pgvector</Badge>
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-300">
              Your request is converted into dense 384-dimensional embeddings using all-MiniLM-L6-v2 on our PostgreSQL engine.
            </p>
          </div>
        </div>

        <Link
          to="/requests"
          className="text-xs font-semibold text-brand-primary dark:text-teal-300 flex items-center gap-1 hover:underline whitespace-nowrap min-h-[32px]"
        >
          View All Requests <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </Card>

      {/* Recent Requests Section */}
      {recentRequests.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-primary" />
              Your Recent Requests
            </h2>
            <Link
              to="/requests"
              className="text-xs font-medium text-brand-primary dark:text-teal-400 hover:underline min-h-[32px] flex items-center"
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
      )}
    </div>
  );
}

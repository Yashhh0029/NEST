import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { profileService } from "@/services/profile";
import type { PublicProfile } from "@/types/profile";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Reveal } from "@/components/motion";
import {
  MapPin,
  Star,
  ShieldCheck,
  CheckCircle2,
  ArrowLeft,
  Award,
  Sparkles,
} from "lucide-react";

export function HelperProfilePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    profileService
      .getPublicProfile(id)
      .then((data) => {
        setProfile(data);
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || "Could not load helper profile.";
        setError(msg);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
        <Skeleton className="h-6 w-32 rounded-lg" />
        <Card className="p-8 space-y-6">
          <div className="flex items-center gap-6">
            <Skeleton className="w-20 h-20 rounded-full" />
            <div className="space-y-3 flex-1">
              <Skeleton className="h-8 w-48 rounded-lg" />
              <Skeleton className="h-4 w-72 rounded-lg" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
          </div>
        </Card>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="max-w-md mx-auto py-16 px-4 text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-3xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold text-2xl">
          ⚠️
        </div>
        <h2 className="text-xl font-bold font-heading text-slate-900 dark:text-white">
          Profile Unavailable
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {error || "This helper profile could not be found or has privacy restrictions enabled."}
        </p>
        <Button onClick={() => navigate(-1)} variant="outline" className="gap-2">
          <ArrowLeft className="w-4 h-4" /> Go Back
        </Button>
      </div>
    );
  }

  const { user, profile: p, location: loc, skills, reputation, public_availability: avail } = profile;

  // Determine Flock Tier from review count
  const reviewCount = reputation?.review_count || 0;
  const avgRating = reputation?.average_rating;
  const getFlockTier = (count: number, rating?: number | null) => {
    if (count >= 10 || (rating && rating >= 4.8 && count >= 5)) {
      return {
        icon: "🦅",
        name: "Roost Guide",
        description: "Distinguished local mentor with verified community track record.",
        nextTier: null,
        progress: 100,
        badgeColor: "bg-teal-700 text-amber-300",
      };
    }
    if (count >= 5) {
      return {
        icon: "🐥",
        name: "Fledgling",
        description: "Experienced helper with multiple successful newcomer sessions.",
        nextTier: "Roost Guide (10 sessions)",
        progress: Math.min(100, Math.round((count / 10) * 100)),
        badgeColor: "bg-amber-600 text-white",
      };
    }
    if (count >= 1) {
      return {
        icon: "🐣",
        name: "Hatchling",
        description: "Verified active helper with completed newcomer assistance.",
        nextTier: "Fledgling (5 sessions)",
        progress: Math.min(100, Math.round((count / 5) * 100)),
        badgeColor: "bg-emerald-600 text-white",
      };
    }
    return {
      icon: "🥚",
      name: "Egg",
      description: "Newly enrolled local resident ready to welcome newcomers.",
      nextTier: "Hatchling (1 session)",
      progress: 15,
      badgeColor: "bg-slate-600 text-white",
    };
  };

  const tier = getFlockTier(reviewCount, avgRating);

  return (
    <div className="max-w-4xl mx-auto py-4 sm:py-8 px-4 space-y-8">
      {/* Top back navigation */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-teal-700 dark:text-teal-400 hover:underline cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* Main Profile Header Card */}
      <Reveal direction="up">
        <Card className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
          {/* Subtle gradient corner accent */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 relative z-10">
            <div className="flex items-center gap-5">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-teal-600 to-amber-500 text-white flex items-center justify-center font-heading font-extrabold text-3xl shadow-md">
                {user.name.charAt(0).toUpperCase()}
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h1 className="text-2xl sm:text-3xl font-extrabold font-heading text-slate-900 dark:text-white">
                    {user.name}
                  </h1>
                  <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${tier.badgeColor}`}>
                    <span>{tier.icon}</span>
                    <span>{tier.name}</span>
                  </span>
                </div>

                <p className="text-sm font-medium text-teal-700 dark:text-teal-300">
                  {p?.headline || "Local Guide & Community Helper"}
                </p>

                {loc && (
                  <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                    <MapPin className="w-3.5 h-3.5 text-teal-600" />
                    <span>
                      {[loc.area, loc.city, loc.state].filter(Boolean).join(", ")}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Availability status badge */}
            <div className="flex flex-col sm:items-end gap-1.5">
              <span
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold ${
                  avail?.capacity_status === "AVAILABLE"
                    ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    avail?.capacity_status === "AVAILABLE" ? "bg-emerald-500 animate-pulse" : "bg-slate-400"
                  }`}
                />
                {avail?.capacity_status === "AVAILABLE" ? "Accepting Sessions" : "Limited Availability"}
              </span>
              <span className="text-[11px] text-slate-400">
                Timezone: {avail?.helper_timezone || "Asia/Kolkata"}
              </span>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-slate-100 dark:border-slate-800">
            <div className="space-y-0.5">
              <span className="text-xs text-slate-400 font-medium">Reputation</span>
              <div className="flex items-center gap-1.5">
                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                <span className="font-extrabold text-base text-slate-900 dark:text-white">
                  {avgRating !== null && avgRating !== undefined ? avgRating.toFixed(1) : "New"}
                </span>
                <span className="text-xs text-slate-400">
                  ({reviewCount} review{reviewCount === 1 ? "" : "s"})
                </span>
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-xs text-slate-400 font-medium">Experience</span>
              <div className="font-extrabold text-base text-slate-900 dark:text-white">
                {p?.years_experience ? `${p.years_experience} yrs` : "Local resident"}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-xs text-slate-400 font-medium">Next Available</span>
              <div className="font-extrabold text-base text-slate-900 dark:text-white">
                {avail?.next_available_date || "Check schedule"}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-xs text-slate-400 font-medium">Preferred Windows</span>
              <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
                {avail?.coarse_windows?.length ? avail.coarse_windows.join(", ") : "Flexible"}
              </div>
            </div>
          </div>
        </Card>
      </Reveal>

      {/* Flock Tier Progression Card */}
      <Reveal direction="up" delay={0.1}>
        <Card className="p-6 rounded-3xl bg-gradient-to-br from-slate-900 to-teal-950 text-white border-none shadow-md">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="text-2xl">{tier.icon}</span>
                <div>
                  <h3 className="font-bold font-heading text-white flex items-center gap-2">
                    <span>Flock Tier: {tier.name}</span>
                    <ShieldCheck className="w-4 h-4 text-amber-400" />
                  </h3>
                  <p className="text-xs text-slate-300">{tier.description}</p>
                </div>
              </div>
              {tier.nextTier && (
                <span className="text-xs text-amber-300 font-medium hidden sm:inline">
                  Next: {tier.nextTier}
                </span>
              )}
            </div>

            {/* Progress bar */}
            <div className="space-y-1.5">
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-400 to-teal-400 rounded-full transition-all duration-500"
                  style={{ width: `${tier.progress}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Earned via verified newcomer resolutions</span>
                <span>{tier.progress}% Tier Progress</span>
              </div>
            </div>
          </div>
        </Card>
      </Reveal>

      {/* Details Grid: Bio & Skills */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left 2 Cols: Bio & Help Description */}
        <div className="md:col-span-2 space-y-6">
          <Card className="p-6 rounded-3xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 space-y-4">
            <h2 className="text-lg font-bold font-heading text-slate-900 dark:text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-teal-600" />
              About {user.name.split(" ")[0]}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
              {p?.bio || "This helper has not provided a detailed biography yet, but is actively enrolled to assist newcomers."}
            </p>

            {p?.help_description && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  How I Can Help You
                </h4>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed bg-teal-50/50 dark:bg-teal-950/30 p-4 rounded-2xl border border-teal-100 dark:border-teal-900/50">
                  {p.help_description}
                </p>
              </div>
            )}
          </Card>
        </div>

        {/* Right 1 Col: Verified Skills & Languages */}
        <div className="space-y-6">
          <Card className="p-6 rounded-3xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-sm font-bold font-heading text-slate-900 dark:text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-500" />
              Verified Local Expertise
            </h3>

            {skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {skills.map((s) => (
                  <span
                    key={s.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                    <span>{s.skill_name}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No specific skills listed yet.</p>
            )}

            {p?.languages && p.languages.length > 0 && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Spoken Languages
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {p.languages.map((lang, idx) => (
                    <Badge key={idx} variant="neutral" size="sm">
                      {lang}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

import type { FullProfile } from "@/types/profile";
import { Link } from "react-router-dom";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { Briefcase, MapPin, Globe, CheckCircle2, XCircle } from "lucide-react";

export interface ProfileHeaderProps {
  fullProfile: FullProfile;
}

export function ProfileHeader({ fullProfile }: ProfileHeaderProps) {
  const { user, profile, location } = fullProfile;

  const roleLabels: Record<string, string> = {
    newcomer: "New to the City",
    helper: "Local Community Helper",
    both: "Newcomer & Helper",
  };

  return (
    <Card className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-teal-100 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-heading font-bold text-2xl shadow-soft">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
                {user.name}
              </h1>
              <Badge variant="primary" size="sm">
                {roleLabels[user.role] || user.role}
              </Badge>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{user.email}</p>
          </div>
        </div>

        {/* Availability Badge */}
        {profile && (
          <Badge
            variant={profile.availability ? "success" : "neutral"}
            size="sm"
            icon={
              profile.availability ? (
                <CheckCircle2 className="w-3.5 h-3.5" />
              ) : (
                <XCircle className="w-3.5 h-3.5" />
              )
            }
          >
            {profile.availability ? "Accepting Connections" : "Currently Busy"}
          </Badge>
        )}
      </div>

      {/* Headline & Bio */}
      {profile?.headline && (
        <p className="text-base font-medium text-gray-800 dark:text-gray-200">
          {profile.headline}
        </p>
      )}

      {profile?.bio && (
        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          {profile.bio}
        </p>
      )}

      {/* Meta Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 text-sm">
        {/* Location */}
        {location ? (
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <MapPin className="w-4 h-4 text-brand-primary shrink-0" />
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {location.display_name && location.display_name !== location.city && location.display_name !== location.area
                  ? `${location.display_name}, ${[location.area, location.city].filter(Boolean).join(", ")}`
                  : [location.area, location.city].filter(Boolean).join(", ")}
              </span>
              <Link
                to="/profile/edit#location"
                className="text-xs text-brand-primary dark:text-teal-400 hover:underline font-normal inline-flex items-center gap-0.5 ml-1"
              >
                (Edit Location)
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-amber-500 shrink-0" />
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-gray-500 dark:text-gray-400 text-sm italic">
                Location not set
              </span>
              <Link
                to="/profile/edit#location"
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-brand-primary/10 text-brand-primary dark:bg-teal-400/20 dark:text-teal-300 hover:bg-brand-primary/20 transition-colors"
              >
                Set Location →
              </Link>
            </div>
          </div>
        )}

        {/* Occupation */}
        {profile?.occupation && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
            <Briefcase className="w-4 h-4 text-brand-primary shrink-0" />
            <span>
              {profile.occupation}
              {profile.organization ? ` at ${profile.organization}` : ""}
            </span>
          </div>
        )}

        {/* Languages */}
        {profile?.languages && profile.languages.length > 0 && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
            <Globe className="w-4 h-4 text-brand-primary shrink-0" />
            <span>{profile.languages.join(", ")}</span>
          </div>
        )}
      </div>
    </Card>
  );
}

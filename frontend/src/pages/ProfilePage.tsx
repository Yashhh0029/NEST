import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { profileService } from "@/services/profile";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { SkillBadgeList } from "@/components/profile/SkillBadgeList";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { CardSkeleton } from "@/components/ui/Skeleton";
import type { FullProfile } from "@/types/profile";
import { Edit3, Sparkles, Award } from "lucide-react";

export function ProfilePage() {
  const [profileData, setProfileData] = useState<FullProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    profileService
      .getMyProfile()
      .then((data) => setProfileData(data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-6 space-y-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center text-sm text-gray-500">
        Could not load profile. Please refresh.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-2 sm:py-6 space-y-6">
      {/* Top action row */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100">
          Your Profile
        </h1>
        <Link to="/profile/edit">
          <Button variant="outline" size="sm" leftIcon={<Edit3 className="w-3.5 h-3.5" />}>
            Edit Profile
          </Button>
        </Link>
      </div>

      {/* Main Profile Header */}
      <ProfileHeader fullProfile={profileData} />

      {/* Detailed Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Help & Needs Details */}
        <Card className="space-y-4">
          <div className="flex items-center gap-2 text-brand-primary dark:text-teal-400 font-bold font-heading">
            <Sparkles className="w-5 h-5 text-amber-500" />
            <span>Community Assistance Scope</span>
          </div>

          <div className="space-y-3 text-sm">
            <div>
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 block mb-1">
                What I can advise or help newcomers with:
              </span>
              <p className="text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-brand-dark-muted/20 p-3 rounded-xl border border-gray-200/60 dark:border-brand-dark-border">
                {profileData.profile?.help_description || "No specific advice areas described yet."}
              </p>
            </div>

            <div>
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 block mb-1">
                Assistance I'm currently looking for:
              </span>
              <p className="text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-brand-dark-muted/20 p-3 rounded-xl border border-gray-200/60 dark:border-brand-dark-border">
                {profileData.profile?.needs_description || "No specific newcomer needs described yet."}
              </p>
            </div>
          </div>
        </Card>

        {/* Skills & Knowledge Areas */}
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-brand-primary dark:text-teal-400 font-bold font-heading">
              <Award className="w-5 h-5" />
              <span>Skills & Expertise</span>
            </div>
            <Link
              to="/profile/edit"
              className="text-xs text-brand-primary dark:text-teal-400 hover:underline"
            >
              Manage
            </Link>
          </div>

          <SkillBadgeList skills={profileData.skills || []} isEditable={false} />
        </Card>
      </div>
    </div>
  );
}
